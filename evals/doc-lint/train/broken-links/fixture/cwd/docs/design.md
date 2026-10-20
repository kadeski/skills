# Design

## Parsing

Each line is split on the first space: a timestamp, then the event name. The parser lives in `parse/parse.go`. Lines that fail to parse are counted, not dropped.

## Summary format

The daily summary has one row per event: name, count, first seen, last seen.

## Failure handling

A bad release is undone by hand; see [how to roll back](ops.md#rollback).
