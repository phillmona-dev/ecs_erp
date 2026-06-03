# Odoo 19 Local Docker Setup

This folder runs Odoo 19 Community with PostgreSQL 15.

## Start

```bash
cd /home/phillmon/Documents/mypros/y/ECS
sudo docker compose -f odoo19/docker-compose.yml up -d
```

Open Odoo at:

```text
http://localhost:8070
```

The stack starts Odoo with the `ecs_odoo19` database and automatically installs/updates the ECS modules plus `ecs_theme`. After login, users land on the customized ECS app launcher showing installed ECS apps first.

On the first screen, create a new database.

- Master password: `admin`
- Database user: managed automatically by Docker
- Odoo addons path: this repository is mounted at `/mnt/extra-addons`

## Manage

```bash
sudo docker compose -f odoo19/docker-compose.yml ps
sudo docker compose -f odoo19/docker-compose.yml logs -f odoo
sudo docker compose -f odoo19/docker-compose.yml stop
sudo docker compose -f odoo19/docker-compose.yml start
sudo docker compose -f odoo19/docker-compose.yml down
```

## Optional: avoid sudo for Docker

```bash
sudo usermod -aG docker "$USER"
```

Log out and back in after running that command.
