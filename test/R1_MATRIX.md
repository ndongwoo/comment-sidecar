# R1 compatibility test matrix

This harness is for development/CI only. It does not change the production
runtime requirement: production remains Apache + PHP + MariaDB/MySQL, with no
Docker, Node.js server, Python server, Redis, worker, or cron requirement.

Run the fast DB-free PHP runtime checks first:

```bash
./test/r1_php_smoke.sh
```

Run the existing upstream pytest integration suite across the R1 target matrix:

```bash
poetry install
./test/run_r1_matrix.sh
```

The matrix is:

- PHP 8.2 + MariaDB 11.4
- PHP 8.4 + MariaDB 11.4
- PHP 8.2 + MySQL 8.4

`Dockerfile.r1` and `docker-compose.r1.yml` are test-only assets. The production
deployment remains upload-only PHP/JS/CSS/SQL.
