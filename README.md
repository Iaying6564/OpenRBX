# OpenRBX

[Discord](https://discord.gg/2JcBQFxVPv) | [Contributing](/CONTRIBUTING.md)

This is a decompilation of Roblox as it was released in December 2007. We're writing the source back until Visual C++ compiles it into the same binaries, instruction for instruction, and the end goal is a codebase we can build on.

We follow the conventions and tooling of the [LEGO Racers decompilation](https://github.com/isledecomp/racers).

Keep in mind that this code reproduces the original release as it was, bugs included. It only builds for 32-bit Windows.

## Progress

<p align="center"><a href="https://asphaltian.github.io/OpenRBX/ROBLOXPROGRESS.HTML"><img src="https://asphaltian.github.io/OpenRBX/ROBLOXPROGRESS.SVG" width="45%"></a> <a href="https://asphaltian.github.io/OpenRBX/WEBSERVICEPROGRESS.HTML"><img src="https://asphaltian.github.io/OpenRBX/WEBSERVICEPROGRESS.SVG" width="45%"></a></p>

All but ~140 of the Roblox functions in `WebService.dll` from RBXGS, the game server, compile to the same instructions as the original.

The client, `Roblox.exe`, is currently being worked on. Both binaries were built from the same engine libraries, so a little over a third of it already matches.

## Building

You will need:

* Visual C++ 8.0 SP1. [MSVC800-SP1](https://github.com/Asphaltian/MSVC800-SP1) is a portable copy that doesn't need installing. Use it for the engine and remaining sources.
* Visual C++ 8.0 RTM for zlib. Use [archaic-msvc/msvc800](https://github.com/archaic-msvc/msvc800) at revision `00ddaf58d09788f0b12e475dae5fb5674dd32578` (`cl.exe` 14.00.50727.42). CMake selects this compiler only for zlib; keep the SP1 environment, headers, libraries and linker active.
* [CMake](https://cmake.org/), either standalone or the one that comes with the "Desktop development with C++" workload in a recent Visual Studio.

Open a command prompt and run `Common7\Tools\vsvars32.bat` from the toolchain folder. Don't use `VC\bin\vcvars32.bat`, it looks for a registered Visual Studio 2005 install and won't work with the portable copy.

Fetch the pinned RTM compiler, then configure and build:

```
git clone https://github.com/archaic-msvc/msvc800.git msvc800rtm
git -C msvc800rtm checkout 00ddaf58d09788f0b12e475dae5fb5674dd32578
cmake -B build -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

This gives you `build\WebService.dll` and `build\Roblox.exe`. Stick with `RelWithDebInfo`, comparing your build against the original needs the debug symbols it produces.

CMake finds RTM in `msvc800rtm/VC/bin`, `msvc800-rtm/VC/bin`, or the build directory's `msvc800-rtm/VC/bin`. For another local cache location, pass `-DOPENRBX_MSVC_RTM_COMPILER=C:/path/to/msvc800/VC/bin/cl.exe`. Ninja works with the same option. Current MSVC builds keep their regular compiler for every source.

The original zlib library carried no debug records. We keep `/Zi` for the rebuilt objects because it preserves private helper names for comparison and produces identical machine code with this compiler.

## Comparing With the Original

You'll need the original binaries. The server's `WebService.dll` comes from the RBXGS 0.3.676.0 installer on [archive.org](https://archive.org/download/rbxgssetup/S3FileHandler_RBXGSSetup_0.3.676.0.msi), and you can pull it out of the `.msi` with [lessmsi](https://github.com/activescott/lessmsi):

```
lessmsi x S3FileHandler_RBXGSSetup_0.3.676.0.msi
```

The DLL ends up in `SourceDir`. Make sure its SHA256 matches before you use it:

```
5e9c6b82605fc8429c5fc5f682f2d7f98b55b73d993dfba58437365754410e2f
```

The client's `Roblox.exe` is the matching 0.3.676.0 build, also on [archive.org](https://archive.org/download/ROBLOX20072013/December%2029%202007%20%280.3.676.0%29.zip/Roblox.exe). Its SHA256 should be:

```
f16069abb753483338ec0ff3a508dc2ee7c696f30997664816446e80863096cc
```

Install our fork of [reccmp](https://github.com/Asphaltian/reccmp/tree/msvc800):

```
pip install -r tools/requirements.txt
```

Create `reccmp-user.yml` in the project root and point it at your copies:

```yaml
targets:
  WEBSERVICE:
    path: path/to/WebService.dll
  ROBLOX:
    path: path/to/Roblox.exe
```

Now you can compare:

```
# the server
reccmp-reccmp --target WEBSERVICE -S WEBSERVICEPROGRESS.SVG

# the client
reccmp-reccmp --target ROBLOX -S ROBLOXPROGRESS.SVG
```

## Project Structure

* `WebService/` - the translation units specific to RBXGS
* `Client/` - the engine's static libraries and client project
* `3rdparty/` - third-party SDKs the original built against from outside its tree
* `util/` - headers the decompilation needs
* `cmake/` - CMake modules
* `tools/` - Python tooling and its requirements
* `reccmp/` - data files for reccmp
* `assets/` - icons for the progress report

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request.
