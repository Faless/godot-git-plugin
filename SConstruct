#!/usr/bin/env python

import os

EnsureSConsVersion(3, 0, 0)
EnsurePythonVersion(3, 5)

opts = Variables([], ARGUMENTS)

env = Environment(ENV=os.environ)

# Define our options
opts.Add(PathVariable("target_path",
         "The path where the lib is installed.", "demo/addons/godot-git-plugin/"))
opts.Add(PathVariable("target_name", "The library name.",
         "libgit_plugin", PathVariable.PathAccept))

# Updates the environment with the option variables.
opts.Update(env)

if ARGUMENTS.get("custom_api_file", "") != "":
    ARGUMENTS["custom_api_file"] = "../" + ARGUMENTS["custom_api_file"]

ARGUMENTS["target"] = "editor"
env = SConscript("godot-cpp/SConstruct").Clone()
opts.Update(env)

# OpenSSL Builder
env.Tool("ssl", toolpath=["tools"])

# Since the OpenSSL build system does not support macOS universal binaries, we first need to build the two libraries
# separately, then we join them together using lipo.
if env["platform"] == "macos" and env["arch"] == "universal":
    build_envs = {
        "x86_64": env.Clone(),
        "arm64": env.Clone(),
    }
    for arch in build_envs:
        benv = build_envs[arch]
        benv["arch"] = arch
        benv.Tool("ssl", toolpath=["tools"])
        ssl = benv.BuildOpenSSL()
        benv.NoCache(ssl)  # Needs refactoring to properly cache generated headers.

    # x86_64 and arm64 includes are equivalent.
    env["SSL_INCLUDE"] = build_envs["arm64"]["SSL_INCLUDE"]

    # Join libraries using lipo.
    ssl_libs = list(map(lambda arch: build_envs[arch]["SSL_LIBRARY"], build_envs))
    ssl_crypto_libs = list(map(lambda arch: build_envs[arch]["SSL_CRYPTO_LIBRARY"], build_envs))
    ssl = [
        env.Command([env["SSL_LIBRARY"]], ssl_libs, "lipo $SOURCES -output $TARGETS -create"),
        env.Command([env["SSL_CRYPTO_LIBRARY"]], ssl_libs, "lipo $SOURCES -output $TARGETS -create"),
    ]

elif env["platform"] == "windows":
    # Windows does not need OpenSSL
    ssl = []

else:
    ssl = env.BuildOpenSSL()
    env.NoCache(ssl)  # Needs refactoring to properly cache generated headers.

Export("env")

SConscript("thirdparty/SCsub")

SConscript("godot-git-plugin/SCsub")

# Generates help for the -h scons option.
Help(opts.GenerateHelpText(env))
