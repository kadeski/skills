package parse

// Line splits a log line into its timestamp and event name.
func Line(s string) (ts, event string, ok bool) {
	for i := 0; i < len(s); i++ {
		if s[i] == ' ' {
			return s[:i], s[i+1:], true
		}
	}
	return "", "", false
}
