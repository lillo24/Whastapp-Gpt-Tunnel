package main

import (
	"context"
	"database/sql"
	_ "embed"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mattn/go-sqlite3"
)

//go:embed schema.sql
var schema string

const timeLayout = "2006-01-02T15:04:05.000000Z"

var errStore = errors.New("STORAGE_UNAVAILABLE")

type Store struct {
	db   *sql.DB
	lock *os.File
	dir  string
}
type Record struct {
	ID        string `json:"id"`
	Chat      string `json:"chat_jid"`
	Sender    string `json:"sender"`
	Content   string `json:"content"`
	Timestamp string `json:"timestamp"`
	Own       int    `json:"is_from_me"`
	Media     string `json:"media_type"`
	Name      string `json:"chat_name"`
}

func stamp(t time.Time) string { return t.UTC().Format(timeLayout) }
func normalizeTime(value any) (string, error) {
	if t, ok := value.(time.Time); ok {
		if t.IsZero() {
			return "", errStore
		}
		return stamp(t), nil
	}
	s, ok := value.(string)
	if !ok {
		return "", errStore
	}
	for _, layout := range []string{time.RFC3339Nano, "2006-01-02 15:04:05.999999999-07:00", "2006-01-02 15:04:05.999999999 -0700 MST"} {
		if t, err := time.Parse(layout, s); err == nil && !t.IsZero() {
			return stamp(t), nil
		}
	}
	return "", errStore // Never guess the zone of a legacy naive timestamp.
}
func sqliteURI(path string) string {
	u := url.URL{Scheme: "file", Path: "/" + strings.TrimPrefix(filepath.ToSlash(path), "/")}
	q := u.Query()
	q.Set("_foreign_keys", "on")
	q.Set("_busy_timeout", "5000")
	u.RawQuery = q.Encode()
	return u.String()
}
func openStore(dir string) (*Store, error) {
	if err := secureDir(dir); err != nil {
		return nil, err
	}
	lock, err := writerLock(filepath.Join(dir, "collector.lock"))
	if err != nil {
		return nil, errors.New("WRITER_ALREADY_RUNNING")
	}
	db, err := sql.Open("sqlite3", sqliteURI(filepath.Join(dir, "messages.db")))
	if err != nil {
		lock.Close()
		return nil, errStore
	}
	db.SetMaxOpenConns(1)
	s := &Store{db, lock, dir}
	if err = s.initialize(); err != nil {
		s.Close()
		return nil, errStore
	}
	return s, nil
}
func (s *Store) Close() { s.db.Close(); s.lock.Close() }
func (s *Store) initialize() error {
	var version int
	if err := s.db.QueryRow("PRAGMA user_version").Scan(&version); err != nil {
		return err
	}
	if version != 0 && version != 1 {
		return errStore
	}
	var tables int
	if err := s.db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").Scan(&tables); err != nil {
		return err
	}
	if version == 0 && tables > 0 {
		if err := secureDir(filepath.Join(s.dir, "backups")); err != nil {
			return err
		}
		backup := filepath.Join(s.dir, "backups", fmt.Sprintf("pre-v1-%d.db", time.Now().UnixNano()))
		if err := s.backup(backup); err != nil {
			return err
		}
	}
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if version == 0 && tables > 0 {
		rows, e := tx.Query("SELECT id,chat_jid,timestamp FROM messages")
		if e != nil {
			return e
		}
		type dateRow struct{ id, chat, date string }
		var dates []dateRow
		for rows.Next() {
			var id, chat string
			var value any
			if e = rows.Scan(&id, &chat, &value); e != nil {
				rows.Close()
				return e
			}
			date, e := normalizeTime(value)
			if e != nil || id == "" || chat == "" {
				rows.Close()
				return errStore
			}
			dates = append(dates, dateRow{id, chat, date})
		}
		e = rows.Err()
		rows.Close()
		if e != nil {
			return e
		}
		for _, d := range dates {
			if _, e = tx.Exec("UPDATE messages SET timestamp=? WHERE id=? AND chat_jid=?", d.date, d.id, d.chat); e != nil {
				return e
			}
		}
		rows, e = tx.Query("SELECT jid,last_message_time FROM chats")
		if e != nil {
			return e
		}
		var chatDates []dateRow
		for rows.Next() {
			var id string
			var value any
			if e = rows.Scan(&id, &value); e != nil {
				rows.Close()
				return e
			}
			if value == nil {
				continue
			}
			date, e := normalizeTime(value)
			if e != nil {
				rows.Close()
				return e
			}
			chatDates = append(chatDates, dateRow{id, "", date})
		}
		e = rows.Err()
		rows.Close()
		if e != nil {
			return e
		}
		for _, d := range chatDates {
			if _, e = tx.Exec("UPDATE chats SET last_message_time=? WHERE jid=?", d.date, d.id); e != nil {
				return e
			}
		}
	}
	ddl := strings.ReplaceAll(strings.ReplaceAll(schema, "CREATE TABLE ", "CREATE TABLE IF NOT EXISTS "), "CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ")
	if _, err = tx.Exec(ddl); err != nil {
		return err
	}
	if _, err = tx.Exec("INSERT OR IGNORE INTO collector_status(singleton,linked,connected,heartbeat_at,partial_history,synthetic) VALUES(1,0,0,?,1,0)", stamp(time.Now())); err != nil {
		return err
	}
	if err = tx.Commit(); err != nil {
		return err
	}
	var integrity string
	if err = s.db.QueryRow("PRAGMA quick_check").Scan(&integrity); err != nil || integrity != "ok" {
		return errStore
	}
	if _, err = s.db.Exec("PRAGMA journal_mode=WAL"); err != nil {
		return err
	}
	_, err = s.db.Exec("PRAGMA synchronous=FULL")
	return err
}
func (s *Store) status(linked, connected, synthetic bool, class string) error {
	now := stamp(time.Now())
	_, err := s.db.Exec(`UPDATE collector_status SET linked=?,last_connected_at=CASE WHEN ? AND connected=0 THEN ? ELSE last_connected_at END,
 connected=?,synthetic=?,heartbeat_at=?,error_class=NULLIF(?,'') WHERE singleton=1`, linked, connected, now, connected, synthetic, now, class)
	return err
}
func (s *Store) ingest(records []Record, live, history bool) error {
	tx, err := s.db.Begin()
	if err != nil {
		return errStore
	}
	defer tx.Rollback()
	for _, r := range records {
		if r.ID == "" || r.Chat == "" || r.Sender == "" || (r.Own != 0 && r.Own != 1) || len(r.ID) > 256 || len(r.Chat) > 256 || len(r.Sender) > 256 {
			return errors.New("MALFORMED_EVENT")
		}
		date, err := normalizeTime(r.Timestamp)
		if err != nil {
			return errors.New("MALFORMED_EVENT")
		}
		if r.Content == "" && r.Media == "" {
			continue
		}
		if _, err = tx.Exec(`INSERT INTO chats(jid,name) VALUES(?,NULLIF(?,''))
			ON CONFLICT(jid) DO UPDATE SET name=COALESCE(NULLIF(excluded.name,''),chats.name)`, r.Chat, r.Name); err != nil {
			return errStore
		}
		insert, err := tx.Exec(`INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me,media_type)
			VALUES(?,?,?,?,?,?,?) ON CONFLICT(id,chat_jid) DO NOTHING`, r.ID, r.Chat, r.Sender, r.Content, date, r.Own, r.Media)
		if err != nil {
			return errStore
		}
		changed, err := insert.RowsAffected()
		if err != nil {
			return errStore
		}
		if changed > 0 {
			if _, err = tx.Exec("UPDATE chats SET last_message_time=MAX(COALESCE(last_message_time,''),?) WHERE jid=?", date, r.Chat); err != nil {
				return errStore
			}
		}
	}
	now := stamp(time.Now())
	if _, err = tx.Exec(`UPDATE collector_status SET last_db_update_at=?,last_receive_at=CASE WHEN ? THEN ? ELSE last_receive_at END,
 last_history_event_at=CASE WHEN ? THEN ? ELSE last_history_event_at END WHERE singleton=1`, now, live, now, history, now); err != nil {
		return errStore
	}
	return tx.Commit()
}
func (s *Store) backup(destination string) error {
	if _, err := os.Stat(destination); !errors.Is(err, os.ErrNotExist) {
		return errStore
	}
	dst, err := sql.Open("sqlite3", sqliteURI(destination))
	if err != nil {
		return err
	}
	defer dst.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	srcConn, err := s.db.Conn(ctx)
	if err != nil {
		return err
	}
	defer srcConn.Close()
	dstConn, err := dst.Conn(ctx)
	if err != nil {
		return err
	}
	defer dstConn.Close()
	return srcConn.Raw(func(src any) error {
		return dstConn.Raw(func(d any) error {
			b, err := d.(*sqlite3.SQLiteConn).Backup("main", src.(*sqlite3.SQLiteConn), "main")
			if err != nil {
				return err
			}
			defer b.Close()
			for {
				done, e := b.Step(128)
				if e != nil {
					return e
				}
				if done {
					return b.Finish()
				}
				select {
				case <-ctx.Done():
					return ctx.Err()
				case <-time.After(10 * time.Millisecond):
				}
			}
		})
	})
}
