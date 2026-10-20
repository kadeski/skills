package sync

// Winner returns the edit with the later server timestamp.
func Winner(a, b Edit) Edit {
	if b.ServerTime.After(a.ServerTime) {
		return b
	}
	return a
}
