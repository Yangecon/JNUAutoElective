# Design

## System

JNUAutoElective uses a restrained product UI style: system sans typography, compact panels, familiar buttons, table-like candidate rows, and clear status badges.

## Color

- Background: cool near-white `oklch(96.5% 0.012 220)`
- Surface: white
- Secondary surface: `oklch(98.2% 0.006 220)`
- Ink: `oklch(22% 0.035 230)`
- Muted text: `oklch(45% 0.03 230)`
- Accent: `oklch(43% 0.095 220)`
- Success: `oklch(43% 0.12 155)`
- Danger: `oklch(45% 0.16 25)`

## Typography

Use `"Segoe UI", "Microsoft YaHei", Arial, sans-serif`. Keep headings modest and fixed-size. Use monospace only for logs and multi-line class input.

## Components

- Top bar: brand mark, navigation, login/run badges.
- Search panel: textarea, retry interval, query/add/login/start actions.
- Pending list: compact repeated rows with remove buttons.
- Candidate list: dense selectable rows with course name, class ID, teacher, department, time, and place.
- Log panel: dark operational console.
- Schedule page: standalone 7-day by 13-section grid with a return button.
- Start controls: official start time in Asia/Shanghai, lead seconds, and high-frequency submit interval.

## Interaction

Search results are not automatically抢课 targets. Users explicitly add checked candidates to the pending list. Start uses only pending courses, waits until the configured Asia/Shanghai start time minus lead seconds, then retries until success or stop.
