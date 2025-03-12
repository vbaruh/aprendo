REPO_ROOT := ..

.PHONY: venv backend frontend clean build-all

venv:
	docker build -t aprendo-venv -f Dockerfile.venv $(REPO_ROOT)

backend: venv
	docker build -t aprendo-backend -f Dockerfile.backend $(REPO_ROOT)

frontend: venv
	docker build -t aprendo-frontend -f Dockerfile.frontend $(REPO_ROOT)

build-all: venv backend frontend
	echo "Building all deployment targets"

export-images: build-all
	echo "Exporting backend image"
	mkdir -p $(REPO_ROOT)/build
	docker save -o $(REPO_ROOT)/build/aprendo-backend.tar aprendo-backend
	docker save -o $(REPO_ROOT)/build/aprendo-frontend.tar aprendo-frontend

clean:
	# Add commands to clean up docker images, containers, etc.
	# docker rmi -f aprendo-backend 2>/dev/null || true
	rm -f $(REPO_ROOT)/build/aprendo-backend.tar
	rm -f $(REPO_ROOT)/build/aprendo-frontend.tar