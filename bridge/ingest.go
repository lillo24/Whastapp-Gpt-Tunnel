package main

import (
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/types/events"
	"strings"
	"time"
)

// Intentionally no handling of edits, deletions, reactions or disappearing wrappers.
// No IDs/content from malformed or unsupported events are ever logged.
func extract(msg *waProto.Message) (string, string) {
	if msg == nil {
		return "", ""
	}
	if text := msg.GetConversation(); text != "" {
		return text, ""
	}
	if m := msg.GetExtendedTextMessage(); m != nil {
		return m.GetText(), ""
	}
	if m := msg.GetImageMessage(); m != nil {
		return m.GetCaption(), "image"
	}
	if m := msg.GetVideoMessage(); m != nil {
		return m.GetCaption(), "video"
	}
	if msg.GetAudioMessage() != nil {
		return "", "audio"
	}
	if msg.GetDocumentMessage() != nil {
		return "", "document"
	}
	return "", ""
}
func liveRecord(event *events.Message) []Record {
	if event == nil || event.Info.Timestamp.IsZero() {
		return nil
	}
	text, media := extract(event.Message)
	if text == "" && media == "" {
		return nil
	}
	own := 0
	if event.Info.IsFromMe {
		own = 1
	}
	return []Record{{ID: event.Info.ID, Chat: event.Info.Chat.String(), Sender: event.Info.Sender.String(), Content: text, Timestamp: stamp(event.Info.Timestamp), Own: own, Media: media}}
}
func historyRecords(event *events.HistorySync, self string) []Record {
	if event == nil || event.Data == nil {
		return nil
	}
	var result []Record
	for _, chat := range event.Data.Conversations {
		if chat == nil || chat.GetID() == "" {
			continue
		}
		name := chat.GetName()
		if name == "" {
			name = chat.GetDisplayName()
		}
		for _, item := range chat.Messages {
			if item == nil || item.Message == nil {
				continue
			}
			info := item.Message
			key := info.Key
			if key == nil || key.GetID() == "" || info.GetMessageTimestamp() == 0 {
				continue
			}
			text, media := extract(info.Message)
			if text == "" && media == "" {
				continue
			}
			sender := key.GetParticipant()
			own := 0
			if key.GetFromMe() {
				own = 1
				sender = self
			} else if sender == "" {
				if strings.HasSuffix(chat.GetID(), "@g.us") {
					sender = "unresolved"
				} else {
					sender = chat.GetID()
				}
			}
			result = append(result, Record{ID: key.GetID(), Chat: chat.GetID(), Sender: sender, Content: text, Timestamp: stamp(time.Unix(int64(info.GetMessageTimestamp()), 0)), Own: own, Media: media, Name: name})
		}
	}
	return result
}
