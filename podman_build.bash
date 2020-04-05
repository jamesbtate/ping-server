#!/bin/bash
podman build --target builder -t ping:builder .
podman build --target base -t ping:base .
podman build --target probe -t ping:probe .
podman build --target collector -t ping:collector .
podman build --target web -t ping:web .
