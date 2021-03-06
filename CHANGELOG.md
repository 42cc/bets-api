# Changelog

## 0.0.9

- add support for `project_id` parameter to `get_bets` method to allow filtering
  by project id in kava

## 0.0.8

- add `get_bets` method (filtering by type, state & ordering by recent stakes
  support)

## 0.0.7

- use API v1.1.3
- increase default timeout to 60 secs
- add method for creating "commit bug" bets (`create_commit_bugs`)

## 0.0.6

- bugfix: gevent.monkey causes https requests to fail under certain
circumstances while doing SSL handshake

## 0.0.5

- uses server API v1.1.1
- `get_active_bets` can filter bets by kava project's id now

## 0.0.4

- uses new version of server API (1.1.0)
- default timeout is 30 seconds
- `get_active_bets` uses pagination (transparent to user)
