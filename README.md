# RBXDecomp

[Discord](https://discord.gg/2JcBQFxVPv) | [Contributing](/CONTRIBUTING.md)

This is a decompilation of Roblox as it was released in December 2007. We're writing the source back until Visual C++ compiles it into the same binaries, instruction for instruction, and the end goal is a codebase we can build on.

We follow the conventions and tooling of the [LEGO Racers decompilation](https://github.com/isledecomp/racers).

Keep in mind that this code reproduces the original release as it was, bugs included. It only builds for 32-bit Windows. If you're after a modern, cross-platform codebase, see [OpenRBX](https://github.com/OpenRBX-org/OpenRBX).

## Progress

<p align="center"><a href="https://openrbx-org.github.io/RBXDecomp/ROBLOXPROGRESS.HTML"><img src="https://openrbx-org.github.io/RBXDecomp/ROBLOXPROGRESS.SVG" width="45%"></a> <a href="https://openrbx-org.github.io/RBXDecomp/WEBSERVICEPROGRESS.HTML"><img src="https://openrbx-org.github.io/RBXDecomp/WEBSERVICEPROGRESS.SVG" width="45%"></a></p>

Both `WebService.dll` from RBXGS, the game server, and the client, `Roblox.exe`, are functionally complete. Work still continues to match the remaining functions.

## Building

You will need:

* Visual C++ 8.0 SP1. [MSVC800-SP1](https://github.com/Asphaltian/MSVC800-SP1) is a portable copy that doesn't need installing. This is the compiler the original was built with, and no other version produces the same code.
* [CMake](https://cmake.org/), either standalone or the one that comes with the "Desktop development with C++" workload in a recent Visual Studio.

Open a command prompt and run `Common7\Tools\vsvars32.bat` from the toolchain folder. Don't use `VC\bin\vcvars32.bat`, it looks for a registered Visual Studio 2005 install and won't work with the portable copy.

Then configure and build:

```
cmake -B build -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

This gives you `build\WebService.dll` and `build\Roblox.exe`. Stick with `RelWithDebInfo`, comparing your build against the original needs the debug symbols it produces.

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
