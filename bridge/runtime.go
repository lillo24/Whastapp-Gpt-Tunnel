package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync/atomic"
	"time"

	"github.com/mdp/qrterminal"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

// Drop all third-party log messages: nested protocol errors may contain secrets.
type discardLog struct{}

func (discardLog) Debugf(string, ...interface{}) {}
func (discardLog) Infof(string, ...interface{})  {}
func (discardLog) Warnf(string, ...interface{})  {}
func (discardLog) Errorf(string, ...interface{}) {}
func (discardLog) Sub(string) waLog.Logger       { return discardLog{} }

func runWhatsApp(ctx context.Context, s *Store, command string) error {
	container, err := sqlstore.New("sqlite3", sqliteURI(filepath.Join(s.dir, "whatsapp.db")), discardLog{})
	if err != nil {
		return errors.New("SESSION_UNAVAILABLE")
	}
	defer container.Close()
	device, err := container.GetFirstDevice()
	if err != nil {
		return errors.New("SESSION_UNAVAILABLE")
	}
	client := whatsmeow.NewClient(device, discardLog{})
	// Reconnection is supervised here with a bounded delay, never QR from a daemon.
	client.EnableAutoReconnect = false
	var revoked atomic.Bool
	client.AddEventHandler(func(event interface{}) {
		var e error
		switch v := event.(type) {
		case *events.Message:
			records := liveRecord(v)
			if len(records) > 0 {
				e = s.ingest(records, true, false)
			}
		case *events.HistorySync:
			self := ""
			if client.Store.ID != nil {
				self = client.Store.ID.ToNonAD().String()
			}
			records := historyRecords(v, self)
			// Keep each transaction bounded; callbacks never log or export their input.
			for start := 0; start < len(records); start += 200 {
				end := start + 200
				if end > len(records) {
					end = len(records)
				}
				if e = s.ingest(records[start:end], false, true); e != nil {
					break
				}
			}
		case *events.LoggedOut:
			revoked.Store(true)
			e = s.status(false, false, false, "RELINK_REQUIRED")
		case *events.Connected:
			e = s.status(true, true, false, "")
		case *events.Disconnected:
			e = s.status(client.Store.ID != nil, false, false, "DISCONNECTED")
		}
		if e != nil {
			fmt.Fprintln(os.Stderr, "bridge: STORAGE_EVENT_FAILED")
		}
	})
	defer client.Disconnect()
	defer func() { s.status(client.Store.ID != nil && !revoked.Load(), false, false, "STOPPED") }()
	if command == "pair" {
		if client.Store.ID != nil {
			return errors.New("ALREADY_LINKED")
		}
		pairCtx, cancel := context.WithTimeout(ctx, 3*time.Minute)
		defer cancel()
		qr, err := client.GetQRChannel(pairCtx)
		if err != nil {
			return errors.New("PAIR_UNAVAILABLE")
		}
		if err = client.Connect(); err != nil {
			return errors.New("CONNECT_FAILED")
		}
		for {
			select {
			case <-pairCtx.Done():
				return errors.New("PAIR_TIMEOUT")
			case event, ok := <-qr:
				if !ok {
					return errors.New("PAIR_INCOMPLETE")
				}
				if event.Event == "code" {
					fmt.Fprintln(os.Stdout, "Scan locally in WhatsApp Linked devices. Do not record this terminal.")
					qrterminal.GenerateHalfBlock(event.Code, qrterminal.L, os.Stdout)
				}
				if event.Event == "success" {
					return s.status(true, client.IsConnected(), false, "")
				}
			}
		}
	}
	if command == "logout" {
		if client.Store.ID == nil {
			return s.status(false, false, false, "NOT_LINKED")
		}
		if err = client.Connect(); err != nil {
			return errors.New("CONNECT_FAILED")
		}
		if err = client.Logout(); err != nil {
			return errors.New("LOGOUT_FAILED")
		}
		revoked.Store(true)
		return s.status(false, false, false, "RELINK_REQUIRED")
	}
	for {
		linked := client.Store.ID != nil && !revoked.Load()
		if !linked {
			if err = s.status(false, false, false, "RELINK_REQUIRED"); err != nil {
				return err
			}
			select {
			case <-ctx.Done():
				return nil
			case <-time.After(30 * time.Second):
				continue
			}
		}
		if !client.IsConnected() {
			err = retryConnection(ctx, func() error {
				if revoked.Load() {
					return errRelink
				}
				if _, e := s.db.Exec("UPDATE collector_status SET last_sync_attempt_at=? WHERE singleton=1", stamp(time.Now())); e != nil {
					return errStore
				}
				return client.Connect()
			}, func() error { return s.status(true, false, false, "CONNECT_FAILED") }, func(d time.Duration) error {
				select {
				case <-ctx.Done():
					return ctx.Err()
				case <-time.After(d):
					return nil
				}
			})
			if errors.Is(err, errRelink) {
				continue
			}
			if err != nil {
				if ctx.Err() != nil {
					return nil
				}
				return err
			}
		}
		connected := client.IsConnected()
		class := ""
		if !connected {
			class = "DISCONNECTED"
		}
		if err = s.status(true, connected, false, class); err != nil {
			return err
		}
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(30 * time.Second):
		}
	}
}

var errRelink = errors.New("RELINK_REQUIRED")

func retryConnection(ctx context.Context, dial func() error, failed func() error, wait func(time.Duration) error) error {
	delay := time.Second
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		err := dial()
		if err == nil {
			return nil
		}
		if errors.Is(err, errRelink) || errors.Is(err, errStore) {
			return err
		}
		if err = failed(); err != nil {
			return err
		}
		if err = wait(delay); err != nil {
			return err
		}
		delay = nextDelay(delay)
	}
}
func nextDelay(delay time.Duration) time.Duration {
	delay *= 2
	if delay > time.Minute {
		return time.Minute
	}
	return delay
}
