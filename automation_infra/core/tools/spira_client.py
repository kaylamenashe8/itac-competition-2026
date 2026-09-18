#!/usr/bin/env python3
"""Minimal SpiraTest/SpiraPlan REST client: connect, list projects, file bugs.

API reference: https://spiradoc.inflectra.com/Developers/API-Overview/

Configuration comes from the environment (or --url / --user on the CLI):

    export SPIRA_URL=https://itac.spiraservice.net
    export SPIRA_USERNAME=kaylamenashe@gmail.com
    export SPIRA_API_KEY='{29142ADC-7527-4251-8EFF-292B1938D37C}'
"""

import argparse
import json
import os
import sys

import requests

DEFAULT_URL = "https://itac.spiraservice.net"
DEFAULT_USERNAME = "kaylamenashe@gmail.com"
DEFAULT_API_KEY = "{29142ADC-7527-4251-8EFF-292B1938D37C}"

API_PATH = "Services/v7_0/RestService.svc"

# Lookup name -> (endpoint segment, id field on each row)
LOOKUPS = {
    "priority": ("priorities", "PriorityId"),
    "severity": ("severities", "SeverityId"),
    "type": ("types", "IncidentTypeId"),
    "status": ("statuses", "IncidentStatusId"),
}


class SpiraError(Exception):
    """Raised when Spira returns a non-2xx response."""


class SpiraClient:
    def __init__(self, base_url, username, api_key, timeout=30):
        if not base_url:
            raise ValueError(
                "No Spira URL. Set SPIRA_URL or pass --url "
                "(e.g. https://itac.spiraservice.net)"
            )
        self.base = f"{base_url.rstrip('/')}/{API_PATH}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "username": username,
            "api-key": api_key,
        })
        self._template_ids = {}   # project_id -> template_id
        self._lookup_cache = {}   # (template_id, kind) -> rows

    def _request(self, method, path, **kwargs):
        url = f"{self.base}/{path.lstrip('/')}"
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if not resp.ok:
            # Spira puts the useful part (bad field id, bad project) in the body.
            raise SpiraError(f"{method} {url} -> {resp.status_code}\n{resp.text}")
        if not resp.content:
            return None
        return resp.json()

    # --- reads ---

    def list_projects(self):
        return self._request("GET", "projects")

    def test_connection(self):
        """Verify credentials by fetching the project list."""
        return self.list_projects()

    def list_incidents(self, project_id, start=1, count=25):
        return self._request(
            "GET",
            f"projects/{project_id}/incidents?starting_row={start}&number_rows={count}",
        )

    def template_id(self, project_id):
        """Incident priorities/severities/types live on the project's template."""
        if project_id not in self._template_ids:
            for p in self.list_projects():
                if p["ProjectId"] == project_id:
                    self._template_ids[project_id] = p["ProjectTemplateId"]
                    break
            else:
                raise SpiraError(f"Project {project_id} not visible to this account")
        return self._template_ids[project_id]

    def lookup_rows(self, project_id, kind):
        """Fetch the allowed values for 'priority', 'severity', 'type' or 'status'."""
        segment, _ = LOOKUPS[kind]
        tid = self.template_id(project_id)
        key = (tid, kind)
        if key not in self._lookup_cache:
            self._lookup_cache[key] = self._request(
                "GET", f"project-templates/{tid}/incidents/{segment}"
            )
        return self._lookup_cache[key]

    def resolve(self, project_id, kind, value):
        """Turn 'High' (or '2') into the numeric id Spira wants. None passes through."""
        if value is None:
            return None
        if str(value).isdigit():
            return int(value)

        _, id_field = LOOKUPS[kind]
        rows = self.lookup_rows(project_id, kind)
        needle = str(value).strip().lower()
        for row in rows:
            name = row["Name"].lower()
            # Names look like "2 - High"; match the label or the whole string.
            label = name.split(" - ", 1)[-1]
            if needle in (name, label):
                return row[id_field]
        options = ", ".join(r["Name"] for r in rows)
        raise SpiraError(f"No {kind} matching {value!r}. Options: {options}")

    # --- writes ---

    def create_incident(self, project_id, name, description,
                        priority=None, severity=None, incident_type=None,
                        owner_id=None, detected_release_id=None):
        """File a bug. Priority/severity/type accept names or ids.

        Returns the created incident dict (with IncidentId).
        """
        payload = {
            "Name": name,
            "Description": description,
            "PriorityId": self.resolve(project_id, "priority", priority),
            "SeverityId": self.resolve(project_id, "severity", severity),
            "IncidentTypeId": self.resolve(project_id, "type", incident_type),
            "OwnerId": owner_id,
            "DetectedReleaseId": detected_release_id,
        }
        # Spira rejects some nulls outright; only send what was set.
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request(
            "POST", f"projects/{project_id}/incidents", data=json.dumps(payload)
        )


def build_client(args):
    return SpiraClient(
        base_url=args.url or os.environ.get("SPIRA_URL", DEFAULT_URL),
        username=args.user or os.environ.get("SPIRA_USERNAME", DEFAULT_USERNAME),
        api_key=os.environ.get("SPIRA_API_KEY", DEFAULT_API_KEY),
    )


def main():
    parser = argparse.ArgumentParser(description="Talk to Spira over REST.")
    parser.add_argument("--url", help=f"Spira base URL (default {DEFAULT_URL})")
    parser.add_argument("--user", help="Spira username")

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test", help="Verify credentials")
    sub.add_parser("projects", help="List projects")

    p_list = sub.add_parser("incidents", help="List incidents in a project")
    p_list.add_argument("--project", type=int, required=True)

    p_look = sub.add_parser("lookups", help="Show valid priority/severity/type values")
    p_look.add_argument("--project", type=int, required=True)

    p_bug = sub.add_parser("bug", help="File a bug")
    p_bug.add_argument("--project", type=int, required=True)
    p_bug.add_argument("--name", required=True, help="Bug title")
    p_bug.add_argument("--desc", required=True, help="Description / steps")
    p_bug.add_argument("--priority", help="Name or id, e.g. High or 2")
    p_bug.add_argument("--severity", help="Name or id, e.g. Critical or 1")
    p_bug.add_argument("--type", dest="incident_type", help="Name or id, e.g. Bug")

    args = parser.parse_args()

    try:
        client = build_client(args)

        if args.cmd == "test":
            projects = client.test_connection()
            print(f"Connected. {len(projects)} project(s) visible:")
            for p in projects:
                print(f"  [{p['ProjectId']}] {p['Name']}")

        elif args.cmd == "projects":
            for p in client.list_projects():
                print(f"[{p['ProjectId']}] {p['Name']}")

        elif args.cmd == "incidents":
            rows = client.list_incidents(args.project)
            if not rows:
                print("No incidents.")
            for i in rows:
                print(f"[IN{i['IncidentId']}] {i['Name']} ({i.get('IncidentStatusName')})")

        elif args.cmd == "lookups":
            for kind in LOOKUPS:
                names = [r["Name"] for r in client.lookup_rows(args.project, kind)]
                print(f"{kind:9} {', '.join(names)}")

        elif args.cmd == "bug":
            created = client.create_incident(
                args.project, args.name, args.desc,
                priority=args.priority,
                severity=args.severity,
                incident_type=args.incident_type,
            )
            print(f"Filed IN{created['IncidentId']}: {created['Name']}")

    except (SpiraError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
