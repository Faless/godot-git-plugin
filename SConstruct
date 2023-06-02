#!/usr/bin/env python

import os
import SCons

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

# Since the OpenSSL build system does not support macOS universal binaries, we first need to build the two libraries
# separately, then we join them together using lipo.
mac_universal = env["platform"] == "macos" and env["arch"] == "universal"
build_targets = []
build_envs = [env]

base_env = env

# For macOS universal builds, setup one build environment per architecture.
if mac_universal:
    build_envs = []
    for arch in ["x86_64", "arm64"]:
        env = base_env.Clone()
        env["arch"] = arch
        env["CCFLAGS"] = SCons.Util.CLVar(str(env["CCFLAGS"]).replace("-arch x86_64 -arch arm64", "-arch " + arch))
        env["LINKFLAGS"] = SCons.Util.CLVar(
            str(env["LINKFLAGS"]).replace("-arch x86_64 -arch arm64", "-arch " + arch)
        )
        env["suffix"] = env["suffix"].replace("universal", arch)
        env["OBJSUFFIX"] = env["OBJSUFFIX"].replace("universal", arch)
        env["SHOBJSUFFIX"] = env["suffix"] + env["SHOBJSUFFIX"]
        env["SHLIBSUFFIX"] = env["suffix"] + env["SHLIBSUFFIX"]
        build_envs.append(env)

build_targets = []

# Build our library and its dependencies.
for env in build_envs:

    # Dependencies
    for tool in ["common", "ssl"]:
        env.Tool(tool, toolpath=["tools"])

    if env["platform"] != "windows":
        # Windows uses wincrypt?
        ssl = env.BuildOpenSSL()
        env.NoCache(ssl)  # Needs refactoring to properly cache generated headers.
        env.Prepend(CPPPATH=[env["SSL_INCLUDE"]])
        env.Prepend(LIBPATH=[env["SSL_BUILD"]])
        env.Prepend(LIBS=[env["SSL_LIBS"]])
    else:
        ssl = []

    Export("ssl")
    Export("env")

    SConscript("thirdparty/SCsub")

    build_targets.extend(SConscript("godot-git-plugin/SCsub"))

env = base_env

# For macOS universal builds, join the libraries using lipo.
if mac_universal:
    result_name = "{}{}{}".format(env["target_name"], env["suffix"], env["SHLIBSUFFIX"])

    universal_target = env.Command(
        os.path.join(env["target_path"], result_name), build_targets, "lipo $SOURCES -output $TARGETS -create"
    )
    Default(universal_target)

# Generates help for the -h scons option.
Help(opts.GenerateHelpText(env))
