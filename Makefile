SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE      := docker compose
SERVER_CT    := rag-server
CLIENT_CT    := rag-client
SERVER_URL   := http://localhost:8000
CLIENT_URL   := http://localhost:8501
ENV_FILE     := server/.env
REQUIRED_KEYS := GOOGLE_API_KEY GROQ_API_KEY PINECONE_API_KEY
VENV         := .venv
ifeq ($(OS),Windows_NT)
  PYTHON     := $(CURDIR)/$(VENV)/Scripts/python.exe
else
  PYTHON     := $(CURDIR)/$(VENV)/bin/python
endif

BLUE   := \033[1;34m
GREEN  := \033[1;32m
YELLOW := \033[1;33m
RED    := \033[1;31m
RESET  := \033[0m

step = printf "$(BLUE)==> %s$(RESET)\n" "$(1)"
ok   = printf "$(GREEN)  ✔ %s$(RESET)\n" "$(1)"
warn = printf "$(YELLOW)  ! %s$(RESET)\n" "$(1)"
fail = printf "$(RED)  ✘ %s$(RESET)\n" "$(1)"

.PHONY: help docker-init run stop restart logs status smoke test clean local-install local-run

help:
	@printf "$(BLUE)RAG Medical Assistant$(RESET)\n\n"
	@printf "  $(GREEN)make docker-init$(RESET)   Check Docker + API keys, build the images\n"
	@printf "  $(GREEN)make run$(RESET)           Start server + client in Docker and wait until healthy\n"
	@printf "  $(GREEN)make stop$(RESET)          Stop and remove the containers\n"
	@printf "  $(GREEN)make restart$(RESET)       stop + run\n"
	@printf "  $(GREEN)make logs$(RESET)          Follow the containers' logs (Ctrl+C to quit)\n"
	@printf "  $(GREEN)make status$(RESET)        Show containers and their health\n"
	@printf "  $(GREEN)make test$(RESET)          Run the unit tests (mocked, no API calls)\n"
	@printf "  $(GREEN)make smoke$(RESET)         Check the running containers answer over HTTP\n"
	@printf "  $(GREEN)make clean$(RESET)         Remove containers, images and caches\n"
	@printf "\n  Without Docker:\n"
	@printf "  $(GREEN)make local-install$(RESET) Create .venv and install dependencies\n"
	@printf "  $(GREEN)make local-run$(RESET)     Run server + client directly on this machine\n"

docker-init:
	@$(call step,[1/4] Checking Docker)
	@command -v docker >/dev/null || { $(call fail,docker not installed); exit 1; }
	@$(call ok,$$(docker --version))
	@docker info >/dev/null 2>&1 || { $(call fail,Docker daemon not running - start Docker Desktop); exit 1; }
	@$(call ok,Docker daemon is running)
	@$(call step,[2/4] Checking $(ENV_FILE))
	@test -f $(ENV_FILE) || { $(call fail,$(ENV_FILE) not found - create it with $(REQUIRED_KEYS)); exit 1; }
	@missing=0; for k in $(REQUIRED_KEYS); do \
		if grep -qE "^$$k=.+" $(ENV_FILE); then $(call ok,$$k is set); \
		else $(call fail,$$k is missing or empty); missing=1; fi; \
	done; exit $$missing
	@$(call step,[3/4] Preparing folders)
	@mkdir -p server/uploaded_docs
	@$(call ok,server/uploaded_docs ready (mounted into the server container))
	@$(call step,[4/4] Building images (this can take a few minutes the first time))
	@$(COMPOSE) build
	@$(call ok,Images built:)
	@docker images --format '      {{.Repository}}:{{.Tag}}  {{.Size}}' | grep rag-medical
	@printf "\n$(GREEN)Init done. Next: make run$(RESET)\n"

run:
	@$(call step,[1/3] Checking images)
	@if [ -z "$$(docker images -q rag-medical-server)" ] || [ -z "$$(docker images -q rag-medical-client)" ]; then \
		$(call warn,Images not found - running docker-init first); \
		$(MAKE) --no-print-directory docker-init || exit 1; \
	else $(call ok,Images found); fi
	@$(call step,[2/3] Starting containers)
	@for port in 8000 8501; do \
		pid=$$(lsof -nP -iTCP:$$port -sTCP:LISTEN -t 2>/dev/null | head -1); \
		if [ -n "$$pid" ] && ! docker ps --format '{{.Ports}}' | grep -q ":$$port->"; then \
			$(call fail,Port $$port is already used by another process (PID $$pid: $$(ps -p $$pid -o comm=))); \
			exit 1; \
		fi; \
	done
	@$(COMPOSE) up -d
	@$(call step,[3/3] Waiting for services to be healthy)
	@for ct in $(SERVER_CT) $(CLIENT_CT); do \
		printf "  $$ct "; \
		for i in $$(seq 1 60); do \
			status=$$(docker inspect -f '{{.State.Health.Status}}' $$ct 2>/dev/null); \
			[ "$$status" = "healthy" ] && break; \
			printf "."; sleep 2; \
		done; \
		if [ "$$status" = "healthy" ]; then printf " $(GREEN)healthy$(RESET)\n"; \
		else printf " $(RED)$$status$(RESET)\n"; \
			$(call fail,$$ct did not become healthy. Last logs:); \
			docker logs --tail 30 $$ct; exit 1; fi; \
	done
	@printf "\n$(GREEN)Everything is running:$(RESET)\n"
	@printf "  Frontend (Streamlit): $(CLIENT_URL)\n"
	@printf "  Backend  (FastAPI)  : $(SERVER_URL)  (docs: $(SERVER_URL)/docs)\n"
	@printf "\n  make logs  -> follow logs     make stop -> stop everything\n"

stop:
	@$(call step,Stopping containers)
	@$(COMPOSE) down
	@$(call ok,Containers stopped and removed)

restart: stop run

logs:
	@$(call step,Following logs (Ctrl+C to quit))
	@$(COMPOSE) logs -f --tail 100

status:
	@$(call step,Containers)
	@$(COMPOSE) ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'

smoke:
	@$(call step,Smoke test against running containers)
	@fails=0; \
	check() { \
		code=$$(curl -s -o /dev/null -w '%{http_code}' $$2 || true); \
		if [ "$$code" = "$$3" ]; then $(call ok,$$1 -> HTTP $$code); \
		else $(call fail,$$1 -> HTTP $$code (expected $$3)); fails=1; fi; \
	}; \
	check "GET  /health (server)"  $(SERVER_URL)/health 200; \
	check "GET  /docs   (server)"  $(SERVER_URL)/docs 200; \
	check "POST /ask/ no question" "-X POST $(SERVER_URL)/ask/" 422; \
	check "GET  client health"     $(CLIENT_URL)/_stcore/health 200; \
	check "GET  client page"       $(CLIENT_URL) 200; \
	exit $$fails

test:
	@$(call step,[1/2] Preparing test environment ($(VENV)))
	@test -x $(PYTHON) || uv venv --python 3.12 $(VENV)
	@uv pip install -q -p $(VENV) -r server/requirements-dev.txt
	@$(call ok,Dependencies installed)
	@$(call step,[2/2] Running unit tests (Pinecone / Google / Groq are mocked))
	@cd server && $(PYTHON) -m pytest tests -v -p no:cacheprovider

clean:
	@$(call step,[1/3] Removing containers and images)
	@$(COMPOSE) down --rmi all --remove-orphans 2>/dev/null || true
	@$(call ok,Containers and rag-medical images removed)
	@$(call step,[2/3] Removing Python caches)
	@find . -type d \( -name __pycache__ -o -name .pytest_cache \) -not -path "./$(VENV)/*" -prune -exec rm -rf {} +
	@$(call ok,__pycache__ / .pytest_cache removed)
	@$(call step,[3/3] Kept on purpose)
	@$(call warn,server/uploaded_docs (your PDFs) and $(VENV) are kept - delete manually if needed)

local-install:
	@$(call step,Creating $(VENV) and installing dependencies)
	@test -x $(PYTHON) || uv venv --python 3.12 $(VENV)
	@uv pip install -p $(VENV) -r server/requirements.txt -r client/requirements.txt
	@$(call ok,Local environment ready)

local-run:
	@$(call step,Starting server ($(SERVER_URL)) and client ($(CLIENT_URL)) - Ctrl+C stops both)
	@trap 'kill 0' EXIT INT TERM; \
	( cd server && $(PYTHON) -m uvicorn main:app --reload --port 8000 ) & \
	( cd client && $(PYTHON) -m streamlit run app.py --server.port 8501 --server.headless true ) & \
	wait