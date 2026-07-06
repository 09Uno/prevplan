create table if not exists planning_cases (
    id text primary key,
    created_at timestamptz not null,
    payload jsonb not null
);

create index if not exists planning_cases_created_at_idx
    on planning_cases (created_at desc);

create table if not exists comparison_cases (
    id text primary key,
    created_at timestamptz not null,
    payload jsonb not null
);

create index if not exists comparison_cases_created_at_idx
    on comparison_cases (created_at desc);
