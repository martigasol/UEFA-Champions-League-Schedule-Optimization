# UEFA-Champions-League-Schedule-Optimization

## Description
This project formulates and solves an optimization problem to generate a UEFA Champions League
match schedule that minimizes the total travel distance of teams.

The model respects the official competition constraints while aiming to reduce travel-related
costs and environmental impact.

## Model
The problem is modeled as a binary linear optimization problem using PuLP.

- Decision variable: whether a team plays away against another team
- Objective: minimize total travel distance (Haversine distance between stadiums)
- Solver: CBC (via PuLP)

## Constraints
- Each team plays 8 matches (4 home, 4 away)
- At most one match between any pair of teams
- No matches between teams from the same country
- Maximum of two opponents from the same foreign country
- One home and one away match against each pot

## Data
Team data is read from an Excel file and includes:
- Stadium location (latitude, longitude)
- Country
- Seeding pot
