#pragma once

// Precompiled ATL Server context for MSVC 8 WebService builds.
#define WIN32_LEAN_AND_MEAN
#define _ATL_CSTRING_EXPLICIT_CONSTRUCTORS
#define _ATL_APARTMENT_THREADED
#define _ATL_ATTRIBUTES

#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0501
#endif

// clang-format off
#include <atlsrvres.h>
#include <atlisapi.h>
#include <atlstencil.h>
#include <atlsoap.h>

#include <string>
// clang-format on
