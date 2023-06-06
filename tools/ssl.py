import os
from SCons.Defaults import Mkdir
from SCons.Variables import PathVariable, BoolVariable


def ssl_emitter(target, source, env):
    if env["platform"] == "windows":
        env.AppendUnique(LIBS=["crypt32", "ws2_32"])

    env.Depends(env["SSL_LIBS"], env.File(__file__))
    return env["SSL_LIBS"], [env.Dir(env["SSL_SOURCE"]), env.File(env["SSL_SOURCE"] + "/VERSION.dat")]


def ssl_action(target, source, env):
    build_dir = env["SSL_BUILD"]
    source_dir = env["SSL_SOURCE"]
    install_dir = env["SSL_INSTALL"]

    ssl_env = env.Clone()
    args = [
        "no-ssl2",
        "no-ssl3",
        "no-weak-ssl-ciphers",
        "no-legacy",
        "no-shared",
        "no-tests",
        "--prefix=%s" % install_dir,
        "--openssldir=%s" % install_dir,
    ]
    if env["openssl_debug"]:
        args.append("-d")

    if env["platform"] == "linux":
        if env["arch"] == "x86_32":
            args.extend(["linux-x86"])
        else:
            args.extend(["linux-x86_64"])

    elif env["platform"] == "android":
        api = env["android_api_level"] if int(env["android_api_level"]) > 28 else "28"
        args.extend(
            [
                {
                    "arm64": "android-arm64",
                    "arm32": "android-arm",
                    "x86_32": "android-x86",
                    "x86_64": "android-x86_64",
                }[env["arch"]],
                "-D__ANDROID_API__=%s" % api,
            ]
        )
        # Setup toolchain path.
        ssl_env.PrependENVPath("PATH", os.path.dirname(env["CC"]))
        ssl_env["ENV"]["ANDROID_NDK_ROOT"] = os.environ.get("ANDROID_NDK_ROOT", "")

    elif env["platform"] == "macos":
        if env["arch"] == "x86_64":
            args.extend(["darwin64-x86_64"])
        elif env["arch"] == "arm64":
            args.extend(["darwin64-arm64"])
        else:
            raise ValueError("macOS architecture not supported: %s" % env["arch"])

    elif env["platform"] == "ios":
        if env["ios_simulator"]:
            args.extend(["iossimulator-xcrun"])
        elif env["arch"] == "arm32":
            args.extend(["ios-xcrun"])
        elif env["arch"] == "arm64":
            args.extend(["ios64-xcrun"])
        else:
            raise ValueError("iOS architecture not supported: %s" % env["arch"])

    elif env["platform"] == "windows":
        args.extend(["enable-capieng"])
        if env["arch"] == "x86_32":
            if env["use_mingw"]:
                args.extend(
                    [
                        "mingw",
                        "--cross-compile-prefix=i686-w64-mingw32-",
                    ]
                )
            else:
                args.extend(["VC-WIN32"])
        else:
            if env["use_mingw"]:
                args.extend(
                    [
                        "mingw64",
                        "--cross-compile-prefix=x86_64-w64-mingw32-",
                    ]
                )
            else:
                args.extend(["VC-WIN64A"])

    jobs = env.GetOption("num_jobs")
    ssl_env.Execute(
        [
            Mkdir(build_dir),
            "cd %s && perl %s/Configure %s" % (build_dir, source_dir, " ".join(['"%s"' % a for a in args])),
            "make -C %s -j%s" % (build_dir, jobs),
            "make -C %s install_sw install_ssldirs -j%s" % (build_dir, jobs),
        ]
    )
    return None


def build_openssl(env):
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
            generate(benv)
            ssl = benv.OpenSSLBuilder()
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
    else:
        ssl = env.OpenSSLBuilder()
        env.NoCache(ssl)  # Needs refactoring to properly cache generated headers.

    env.Prepend(CPPPATH=[env["SSL_INCLUDE"]])
    env.Prepend(LIBPATH=[env["SSL_BUILD"]])
    env.Append(LIBS=env["SSL_LIBS"])
    return ssl


def options(opts):
    opts.Add(PathVariable("openssl_source", "Path to the openssl sources.", "thirdparty/openssl"))
    opts.Add("openssl_build", "Destination path of the openssl build.", "bin/thirdparty/openssl")
    opts.Add(BoolVariable("openssl_debug", "Make a debug build of OpenSSL.", False))


def exists(env):
    return True


def generate(env):
    env["SSL_SOURCE"] = env.Dir(env["openssl_source"]).abspath
    env["SSL_BUILD"] = env.Dir(
        env["openssl_build"]
        + "/{}/{}/{}".format(env["platform"], env["arch"], "debug" if env["openssl_debug"] else "release")
    ).abspath
    env["SSL_INSTALL"] = env["SSL_BUILD"] + "/dest"
    env["SSL_INCLUDE"] = env["SSL_INSTALL"] + "/include"
    env["SSL_LIBRARY"] = env.File(env["SSL_BUILD"] + "/libssl.a")
    env["SSL_CRYPTO_LIBRARY"] = env.File(env["SSL_BUILD"] + "/libcrypto.a")
    env["SSL_LIBS"] = [env["SSL_LIBRARY"], env["SSL_CRYPTO_LIBRARY"]]
    env.Append(BUILDERS={"OpenSSLBuilder": env.Builder(action=ssl_action, emitter=ssl_emitter)})
    env.AddMethod(build_openssl, "OpenSSL")
