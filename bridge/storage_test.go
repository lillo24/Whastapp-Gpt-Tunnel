package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/proto/waCommon"
	"go.mau.fi/whatsmeow/proto/waHistorySync"
	"go.mau.fi/whatsmeow/proto/waWeb"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	"google.golang.org/protobuf/proto"
)

func testStore(t *testing.T) *Store {
	t.Helper()
	s, e := openStore(filepath.Join(t.TempDir(), "store"))
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(s.Close)
	return s
}
func example(id, chat, date string) Record {
	return Record{ID: id, Chat: "fixture-" + chat + "@s.whatsapp.net", Sender: "fixture-alice@s.whatsapp.net", Content: "Caffè 你好\nSecond line", Timestamp: date}
}
func count(t *testing.T, db *sql.DB) int {
	t.Helper()
	var n int
	if e := db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&n); e != nil {
		t.Fatal(e)
	}
	return n
}
func TestReplayAttributionAndMonotonicRecency(t *testing.T) {
	s := testStore(t)
	recent := example("shared", "alice", "2024-03-01T01:00:00+02:00")
	recent.Name = "Alex"
	old := example("old", "alice", "2024-02-29T08:00:00Z")
	other := example("shared", "bob", "2024-02-29T09:00:00Z")
	other.Own = 1
	if e := s.ingest([]Record{recent, old, recent, other}, true, true); e != nil {
		t.Fatal(e)
	}
	if count(t, s.db) != 3 {
		t.Fatal("composite deduplication")
	}
	var recency, text string
	var own int
	s.db.QueryRow("SELECT last_message_time FROM chats WHERE jid=?", recent.Chat).Scan(&recency)
	if recency != "2024-02-29T23:00:00.000000Z" {
		t.Fatal(recency)
	}
	s.db.QueryRow("SELECT content,is_from_me FROM messages WHERE id=? AND chat_jid=?", other.ID, other.Chat).Scan(&text, &own)
	if text != other.Content || own != 1 {
		t.Fatal("attribution/text")
	}
	var keys int
	s.db.QueryRow("SELECT COUNT(*) FROM messages WHERE url IS NOT NULL OR media_key IS NOT NULL").Scan(&keys)
	if keys != 0 {
		t.Fatal("media secrets")
	}
}
func TestDuplicateTimestampCannotInventRecency(t *testing.T) {
	s := testStore(t)
	r := example("replay", "alice", "2024-02-29T08:00:00Z")
	if e := s.ingest([]Record{r}, true, false); e != nil {
		t.Fatal(e)
	}
	r.Timestamp = "2099-01-01T00:00:00Z"
	if e := s.ingest([]Record{r}, true, false); e != nil {
		t.Fatal(e)
	}
	var date string
	s.db.QueryRow("SELECT last_message_time FROM chats").Scan(&date)
	if date != "2024-02-29T08:00:00.000000Z" {
		t.Fatal("duplicate invented a future chat date")
	}
}
func TestMalformedBatchRollsBack(t *testing.T) {
	s := testStore(t)
	good := example("ok", "alice", "2024-02-29T08:00:00Z")
	bad := good
	bad.ID = ""
	if s.ingest([]Record{good, bad}, true, false) == nil {
		t.Fatal("expected rejection")
	}
	if count(t, s.db) != 0 {
		t.Fatal("partial transaction")
	}
	bad = good
	bad.Timestamp = "2024-02-29T08:00:00"
	if s.ingest([]Record{bad}, true, false) == nil {
		t.Fatal("naive time accepted")
	}
}
func TestWriterLockAndRestart(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "store")
	s, e := openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = openStore(dir); e == nil {
		t.Fatal("second writer")
	}
	if e = s.ingest([]Record{example("saved", "alice", "2024-02-29T08:00:00Z")}, true, false); e != nil {
		t.Fatal(e)
	}
	s.Close()
	s, e = openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	if count(t, s.db) != 1 {
		t.Fatal("restart loss")
	}
}
func TestConcurrentReadonlyAndBackup(t *testing.T) {
	s := testStore(t)
	reader, e := sql.Open("sqlite3", sqliteURI(filepath.Join(s.dir, "messages.db"))+"&mode=ro")
	if e != nil {
		t.Fatal(e)
	}
	defer reader.Close()
	for i := 0; i < 3; i++ {
		r := example(string(rune('a'+i)), "alice", "2024-02-29T08:00:00Z")
		if e = s.ingest([]Record{r}, true, false); e != nil {
			t.Fatal(e)
		}
		if count(t, reader) != i+1 {
			t.Fatal("reader freshness")
		}
	}
	if _, e = reader.Exec("DELETE FROM messages"); e == nil {
		t.Fatal("writable reader")
	}
	path := filepath.Join(s.dir, "snapshot.db")
	if e = s.backup(path); e != nil {
		t.Fatal(e)
	}
	backup, e := sql.Open("sqlite3", sqliteURI(path)+"&mode=ro")
	if e != nil {
		t.Fatal(e)
	}
	defer backup.Close()
	if count(t, backup) != 3 {
		t.Fatal("backup lost WAL")
	}
}
func TestMigrationPreservesRowsAndSnapshots(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "store")
	os.MkdirAll(dir, 0700)
	db, e := sql.Open("sqlite3", sqliteURI(filepath.Join(dir, "messages.db")))
	if e != nil {
		t.Fatal(e)
	}
	if _, e = db.Exec(schema); e != nil {
		t.Fatal(e)
	}
	db.Exec("DROP TABLE collector_status; PRAGMA user_version=0")
	db.Exec("INSERT INTO chats(jid,name,last_message_time) VALUES('fixture-a','A','2024-02-29 09:00:00+01:00')")
	_, e = db.Exec("INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me) VALUES('m','fixture-a','fixture-a','preserve','2024-02-29 09:00:00+01:00',0)")
	if e != nil {
		t.Fatal(e)
	}
	db.Close()
	s, e := openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	if count(t, s.db) != 1 {
		t.Fatal("migration loss")
	}
	var date string
	s.db.QueryRow("SELECT timestamp FROM messages").Scan(&date)
	if date != "2024-02-29T08:00:00.000000Z" {
		t.Fatal(date)
	}
	files, _ := filepath.Glob(filepath.Join(dir, "backups", "pre-v1-*.db"))
	if len(files) != 1 {
		t.Fatal("missing migration snapshot")
	}
	backup, e := sql.Open("sqlite3", sqliteURI(files[0])+"&mode=ro")
	if e != nil {
		t.Fatal(e)
	}
	defer backup.Close()
	if count(t, backup) != 1 {
		t.Fatal("snapshot content")
	}
}
func TestLiveAndUnsupportedEvents(t *testing.T) {
	event := &events.Message{Info: types.MessageInfo{MessageSource: types.MessageSource{Chat: types.JID{User: "fixture-team", Server: "g.us"}, Sender: types.JID{User: "fixture-alice", Server: "s.whatsapp.net"}, IsFromMe: false}, ID: "synthetic", Timestamp: time.Date(2024, 2, 29, 8, 0, 0, 0, time.UTC)}, Message: &waProto.Message{Conversation: proto.String("Unicode 你好\nreply")}}
	records := liveRecord(event)
	if len(records) != 1 || records[0].Chat != "fixture-team@g.us" || records[0].Sender != "fixture-alice@s.whatsapp.net" {
		t.Fatal("live attribution")
	}
	event.Message = &waProto.Message{ReactionMessage: &waProto.ReactionMessage{Text: proto.String("👍")}}
	if len(liveRecord(event)) != 0 {
		t.Fatal("reaction should be unsupported")
	}
	event.Message = &waProto.Message{ProtocolMessage: &waProto.ProtocolMessage{}}
	if len(liveRecord(event)) != 0 {
		t.Fatal("protocol should be unsupported")
	}
	if liveRecord(nil) != nil || historyRecords(nil, "") != nil {
		t.Fatal("nil")
	}
	text, kind := extract(&waProto.Message{ImageMessage: &waProto.ImageMessage{Caption: proto.String("caption"), URL: proto.String("secret-url")}})
	if text != "caption" || kind != "image" {
		t.Fatal("coarse media")
	}
}
func TestHistoryProtobufAttribution(t *testing.T) {
	group := "fixture-team@g.us"
	self := "fixture-self@s.whatsapp.net"
	other := "fixture-alice@s.whatsapp.net"
	message := func(id string, own bool, participant string) *waHistorySync.HistorySyncMsg {
		return &waHistorySync.HistorySyncMsg{Message: &waWeb.WebMessageInfo{Key: &waCommon.MessageKey{ID: proto.String(id), FromMe: proto.Bool(own), Participant: proto.String(participant)}, Message: &waProto.Message{Conversation: proto.String("old history")}, MessageTimestamp: proto.Uint64(1709193600)}}
	}
	event := &events.HistorySync{Data: &waHistorySync.HistorySync{Conversations: []*waHistorySync.Conversation{{ID: &group, Name: proto.String("Synthetic Team"), Messages: []*waHistorySync.HistorySyncMsg{message("own", true, ""), message("other", false, other), message("unknown", false, "")}}}}}
	records := historyRecords(event, self)
	if len(records) != 3 || records[0].Sender != self || records[0].Own != 1 || records[1].Sender != other || records[2].Sender != "unresolved" {
		t.Fatal("history attribution")
	}
	s := testStore(t)
	if e := s.ingest(records, false, true); e != nil {
		t.Fatal(e)
	}
	if count(t, s.db) != 3 {
		t.Fatal("history count")
	}
}
func TestFixtureCommandAndNegativeCommands(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "store")
	input := filepath.Join(t.TempDir(), "events.json")
	data, _ := json.Marshal(map[string]any{"synthetic": true, "events": []Record{example("one", "alice", "2024-02-29T08:00:00Z")}})
	os.WriteFile(input, data, 0600)
	if e := execute([]string{"fixture", "--synthetic", "--data-dir", dir, "--input", input}); e != nil {
		t.Fatal(e)
	}
	for _, command := range []string{"send", "send_message", "download", "serve-http", "send_file"} {
		if execute([]string{command, "--data-dir", dir}) == nil {
			t.Fatal(command)
		}
	}
	if execute([]string{"pair", "--synthetic", "--data-dir", dir}) == nil {
		t.Fatal("noninteractive pair")
	}
}
func TestRestoredStoreCannotStartOrTouchCredentials(t *testing.T) {
	dir := t.TempDir()
	marker := filepath.Join(dir, ".wa-restored-disconnected")
	os.WriteFile(marker, []byte("wa-operations-v1"), 0600)
	for _, args := range [][]string{
		{"run", "--data-dir", dir},
		{"run", "--synthetic", "--data-dir", dir},
		{"logout", "--data-dir", dir},
		{"fixture", "--synthetic", "--data-dir", dir, "--input", "absent"},
	} {
		if err := execute(args); err == nil || err.Error() != "RESTORED_STORE_DISCONNECTED" {
			t.Fatal("restored session network boundary was not enforced")
		}
	}
	files, _ := os.ReadDir(dir)
	if len(files) != 1 {
		t.Fatal("restored store was modified")
	}
}
func TestDedicatedPathAndBackoff(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "unrelated.txt"), []byte("preserve"), 0600)
	if secureDir(dir) == nil || secureDir("relative") == nil {
		t.Fatal("unsafe directory accepted")
	}
	delay := time.Second
	for i := 0; i < 20; i++ {
		delay = nextDelay(delay)
	}
	if delay != time.Minute {
		t.Fatal("uncapped backoff")
	}
	for _, path := range []string{"main.go", "runtime.go", "ingest.go", "storage.go"} {
		data, _ := os.ReadFile(path)
		for _, bad := range []string{".SendMessage(", ".Upload(", ".Download(", "ListenAndServe", "net/http", "/api/send", "exec.Command"} {
			if strings.Contains(string(data), bad) {
				t.Fatal(path, bad)
			}
		}
	}
}
func TestOfflineReconnectRecoveryAndCancellation(t *testing.T) {
	attempts := 0
	var waits []time.Duration
	err := retryConnection(context.Background(), func() error {
		attempts++
		if attempts < 4 {
			return errors.New("offline fixture-secret")
		}
		return nil
	}, func() error { return nil }, func(d time.Duration) error { waits = append(waits, d); return nil })
	if err != nil || attempts != 4 || len(waits) != 3 || waits[0] != time.Second || waits[2] != 4*time.Second {
		t.Fatal("retry sequence")
	}
	ctx, cancel := context.WithCancel(context.Background())
	calls := 0
	err = retryConnection(ctx, func() error { calls++; return errors.New("offline") }, func() error { return nil }, func(time.Duration) error { cancel(); return ctx.Err() })
	if !errors.Is(err, context.Canceled) || calls != 1 {
		t.Fatal("shutdown did not cancel retry")
	}
}
func TestActiveWriterReadonlySnapshots(t *testing.T) {
	s := testStore(t)
	reader, e := sql.Open("sqlite3", sqliteURI(filepath.Join(s.dir, "messages.db"))+"&mode=ro")
	if e != nil {
		t.Fatal(e)
	}
	defer reader.Close()
	done := make(chan error, 1)
	go func() {
		for i := 0; i < 30; i++ {
			if err := s.ingest([]Record{example(string(rune('A'+i)), "alice", "2024-02-29T08:00:00Z")}, true, false); err != nil {
				done <- err
				return
			}
			time.Sleep(time.Millisecond)
		}
		done <- nil
	}()
	previous := 0
	for {
		n := count(t, reader)
		if n < previous {
			t.Fatal("inconsistent snapshot")
		}
		previous = n
		select {
		case e := <-done:
			if e != nil {
				t.Fatal(e)
			}
			if count(t, reader) != 30 {
				t.Fatal("missing committed rows")
			}
			return
		default:
			time.Sleep(time.Millisecond)
		}
	}
}
