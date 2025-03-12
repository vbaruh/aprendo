# Root Makefile for Aprendo project

.PHONY: build deploy clean

# Build all deployment targets
build:
	$(MAKE) -C deployment build-all

export-images:
	$(MAKE) -C deployment export-images

# Add more deployment targets as needed
# deploy:
# 	$(MAKE) -C deployment deploy

# Clean up
clean:
	$(MAKE) -C deployment clean

# Default target
all: build
