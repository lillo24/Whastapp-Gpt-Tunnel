package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"github.com/mattn/go-isatty"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

func main() {
	if err := execute(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "bridge: operation failed; consult local status and runbook")
		os.Exit(1)
	}
}
func execute(args []string) error {
	if len(args) == 0 {
		return errors.New("COMMAND_REQUIRED")
	}
	command := args[0]
	if command != "run" && command != "pair" && command != "logout" && command != "fixture" && command != "stop" {
		return errors.New("UNKNOWN_COMMAND")
	}
	flags := flag.NewFlagSet("bridge", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	defaultDir := os.Getenv("WA_DATA_DIR")
	if defaultDir == "" {
		defaultDir = filepath.Join(os.Getenv("LOCALAPPDATA"), "WhatsappGptTunnel", "store")
	}
	dir := flags.String("data-dir", defaultDir, "absolute dedicated store")
	synthetic := flags.Bool("synthetic", false, "offline synthetic runtime")
	input := flags.String("input", "", "synthetic event fixture file")
	if err := flags.Parse(args[1:]); err != nil || flags.NArg() != 0 {
		return errors.New("INVALID_ARGUMENTS")
	}
	if !filepath.IsAbs(*dir) {
		return errors.New("INVALID_DATA_DIRECTORY")
	}
	*dir = filepath.Clean(*dir)
	if command == "stop" {
		if *synthetic || *input != "" {
			return errors.New("INVALID_ARGUMENTS")
		}
		return requestStop(*dir)
	}
	// Restored credentials remain quarantined even if an operator accidentally
	// points a scheduled run or pairing command at the inspection directory.
	if _, err := os.Lstat(filepath.Join(*dir, ".wa-restored-disconnected")); err == nil || !os.IsNotExist(err) {
		return errors.New("RESTORED_STORE_DISCONNECTED")
	}
	if (command == "pair" || command == "logout") && (*synthetic || *input != "") {
		return errors.New("INVALID_ARGUMENTS")
	}
	if command == "pair" && (!isatty.IsTerminal(os.Stdin.Fd()) || !isatty.IsTerminal(os.Stdout.Fd())) {
		return errors.New("FOREGROUND_TERMINAL_REQUIRED")
	}
	s, err := openStore(*dir)
	if err != nil {
		return err
	}
	defer s.Close()
	if command == "fixture" {
		if !*synthetic || *input == "" {
			return errors.New("SYNTHETIC_FLAG_REQUIRED")
		}
		var existing int
		if err = s.db.QueryRow("SELECT synthetic FROM collector_status WHERE singleton=1").Scan(&existing); err != nil {
			return err
		}
		var count int
		s.db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&count)
		if count > 0 && existing != 1 {
			return errors.New("PRODUCTION_STORE")
		}
		f, err := os.Open(*input)
		if err != nil {
			return err
		}
		defer f.Close()
		var fixture struct {
			Synthetic bool     `json:"synthetic"`
			Events    []Record `json:"events"`
		}
		if err = json.NewDecoder(io.LimitReader(f, 8<<20)).Decode(&fixture); err != nil || !fixture.Synthetic {
			return errors.New("INVALID_FIXTURE")
		}
		for _, r := range fixture.Events {
			if !strings.HasPrefix(r.Chat, "fixture-") || !strings.HasPrefix(r.Sender, "fixture-") {
				return errors.New("NOT_SYNTHETIC")
			}
		}
		if err = s.ingest(fixture.Events, true, true); err != nil {
			return err
		}
		return s.status(false, false, true, "SYNTHETIC_ONLY")
	}
	os.Remove(filepath.Join(*dir, "stop.request"))
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	go func() {
		timer := time.NewTicker(time.Second)
		defer timer.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-timer.C:
				if _, e := os.Stat(filepath.Join(*dir, "stop.request")); e == nil {
					cancel()
					return
				}
			}
		}
	}()
	if *synthetic {
		var isSynthetic, count int
		s.db.QueryRow("SELECT synthetic FROM collector_status WHERE singleton=1").Scan(&isSynthetic)
		s.db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&count)
		if count > 0 && isSynthetic != 1 {
			return errors.New("PRODUCTION_STORE")
		}
		if *input != "" {
			return errors.New("INVALID_ARGUMENTS")
		}
		defer s.status(false, false, true, "STOPPED")
		for {
			if err = s.status(false, false, true, "SYNTHETIC_ONLY"); err != nil {
				return err
			}
			select {
			case <-ctx.Done():
				return nil
			case <-time.After(30 * time.Second):
			}
		}
	}
	if *input != "" {
		return errors.New("INVALID_ARGUMENTS")
	}
	return runWhatsApp(ctx, s, command)
}
func requestStop(dir string) error {
	info, err := os.Lstat(dir)
	if err != nil || !info.IsDir() {
		return errors.New("INVALID_DATA_DIRECTORY")
	}
	real, err := filepath.EvalSymlinks(dir)
	if err != nil || !strings.EqualFold(real, dir) {
		return errors.New("REDIRECTED_DATA_DIRECTORY")
	}
	if _, err = os.Stat(filepath.Join(dir, ".wa-private-store")); err != nil {
		return errors.New("UNKNOWN_STORE")
	}
	path := filepath.Join(dir, "stop.request")
	if existing, e := os.Lstat(path); e == nil {
		if !existing.Mode().IsRegular() || existing.Size() != 0 {
			return errors.New("INVALID_STOP_FILE")
		}
		return nil
	} else if !os.IsNotExist(e) {
		return e
	}
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	return f.Close()
}
