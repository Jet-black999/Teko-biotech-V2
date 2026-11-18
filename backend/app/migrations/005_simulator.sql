CREATE TABLE simulator_requests (
    request_id TEXT PRIMARY KEY NOT NULL,
    values_json TEXT NOT NULL CHECK (json_valid(values_json)),
    response_json TEXT NOT NULL CHECK (json_valid(response_json)),
    created_at TEXT NOT NULL
);
