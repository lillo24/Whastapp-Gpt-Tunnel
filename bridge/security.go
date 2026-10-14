package main

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

func secureDir(dir string) error {
	if !filepath.IsAbs(dir) || filepath.Clean(dir) != dir || filepath.Dir(dir) == dir {
		return errors.New("INVALID_DATA_DIRECTORY")
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		return errors.New("DATA_DIRECTORY_UNAVAILABLE")
	}
	real, err := filepath.EvalSymlinks(dir)
	if err != nil || !strings.EqualFold(real, dir) {
		return errors.New("REDIRECTED_DATA_DIRECTORY")
	}
	marker := filepath.Join(dir, ".wa-private-store")
	if _, err = os.Stat(marker); os.IsNotExist(err) {
		entries, e := os.ReadDir(dir)
		if e != nil {
			return e
		}
		for _, entry := range entries {
			n := entry.Name()
			if n != "messages.db" && n != "messages.db-wal" && n != "messages.db-shm" && n != "whatsapp.db" && n != "whatsapp.db-wal" && n != "whatsapp.db-shm" {
				return errors.New("NONDEDICATED_DATA_DIRECTORY")
			}
		}
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		p := filepath.Join(dir, entry.Name())
		info, e := os.Lstat(p)
		if e != nil || info.Mode()&os.ModeSymlink != 0 {
			return errors.New("REDIRECTED_DATA_FILE")
		}
		resolved, e := filepath.EvalSymlinks(p)
		if e != nil || !strings.EqualFold(resolved, p) {
			return errors.New("REDIRECTED_DATA_FILE")
		}
	}
	if err = protectDir(dir); err != nil {
		return errors.New("ACL_FAILED")
	}
	f, err := os.OpenFile(marker, os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	return f.Close()
}
