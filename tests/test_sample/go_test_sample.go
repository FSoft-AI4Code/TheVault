// Copyright 2016 The Go Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.
type TypeError struct {
		Type1, Type2 reflect.Type
		Extra        string
	}

// The path package should only be used for paths separated by forward
// slashes, such as the paths in URLs. This package does not deal with
// Windows paths with drive letters or backslashes; to manipulate
// operating system paths, use the [path/filepath] package.
func (e TypeError) Error() string {
		msg := e.Type1.String()
		if e.Type2 != nil {
			msg += " and " + e.Type2.String()
	}
	msg += " " + e.Extra
	return msg
}
