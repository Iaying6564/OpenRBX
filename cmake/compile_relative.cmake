set(original)
set(after_separator FALSE)
set(compiler "")
set(forwarded "")
math(EXPR last "${CMAKE_ARGC} - 1")
foreach(index RANGE ${last})
  if (after_separator)
    set(argument "${CMAKE_ARGV${index}}")
    list(APPEND original "${argument}")
    if (compiler STREQUAL "")
      set(compiler "${argument}")
    elseif (argument MATCHES "[ \t]")
      # Written straight to a response file, never through a list: an argument
      # that ends in a backslash (MSVC passes /Fd<dir>\) would otherwise absorb
      # the separator and the argument after it.
      string(APPEND forwarded "\"${argument}\" ")
    else()
      string(APPEND forwarded "${argument} ")
    endif()
  elseif ("${CMAKE_ARGV${index}}" STREQUAL "--")
    set(after_separator TRUE)
  endif()
endforeach()

if (NOT original)
  message(FATAL_ERROR "compile_relative.cmake needs `-- <compile command>`")
endif()

set(command)
set(response)
foreach(argument IN LISTS original)
  if (argument MATCHES "^@(.+)$")
    set(response "${CMAKE_MATCH_1}")
  elseif (argument MATCHES "^--dep-file=(.+)$")
    get_filename_component(dep_file "${CMAKE_MATCH_1}" ABSOLUTE)
    list(APPEND command "--dep-file=${dep_file}")
  elseif (argument MATCHES "^--working-dir=")
    get_filename_component(source_dir "${SOURCE}" DIRECTORY)
    file(TO_NATIVE_PATH "${source_dir}" working_dir)
    list(APPEND command "--working-dir=${working_dir}")
  else()
    list(APPEND command "${argument}")
  endif()
endforeach()

if (NOT LANGUAGE MATCHES "^(C|CXX)$" OR NOT SOURCE)
  execute_process(COMMAND ${original} RESULT_VARIABLE result)
  if (NOT result EQUAL 0)
    message(FATAL_ERROR "compile_relative.cmake: command failed (${result})")
  endif()
  return()
endif()

get_filename_component(binary_dir "." ABSOLUTE)
file(TO_NATIVE_PATH "${binary_dir}" binary_dir)
string(MD5 key "${SOURCE}")

if (NOT response)
  # Generators without response files (Ninja) hand the command line over as
  # individual arguments. Record it the way NMake does and fall through, so the
  # relocation below applies to every generator.
  set(generated "${binary_dir}/CMakeFiles/compile_relative_in_${key}.rsp")
  file(WRITE "${generated}" "${forwarded}")
  set(response "${generated}")
  # Everything after the compiler now lives in the response file, so the
  # command must not repeat it.
  set(command "${compiler}")
  set(generated_is_temporary TRUE)
endif()

file(TO_NATIVE_PATH "${SOURCE}" source_native)
get_filename_component(source_dir "${SOURCE}" DIRECTORY)
get_filename_component(source_name "${SOURCE}" NAME)

file(READ "${response}" arguments)
string(FIND "${arguments}" "-c ${source_native}" position)
if (position EQUAL -1)
  if (generated_is_temporary)
    file(REMOVE "${response}")
  endif()
  message(FATAL_ERROR "compile_relative.cmake: ${source_native} is not the file being compiled")
endif()
string(REPLACE "-c ${source_native}" "-c .\\${source_name}" arguments "${arguments}")
string(REPLACE " /FoCMakeFiles\\" " /Fo${binary_dir}\\CMakeFiles\\" arguments "${arguments}")
string(REPLACE " /FdCMakeFiles\\" " /Fd${binary_dir}\\CMakeFiles\\" arguments "${arguments}")

set(relocated "${binary_dir}/CMakeFiles/compile_relative_${key}.rsp")
file(WRITE "${relocated}" "${arguments}")

execute_process(
  COMMAND ${command} "@${relocated}"
  WORKING_DIRECTORY "${source_dir}"
  RESULT_VARIABLE result
)
file(REMOVE "${relocated}")
if (generated_is_temporary)
  file(REMOVE "${response}")
endif()
if (NOT result EQUAL 0)
  message(FATAL_ERROR "compile_relative.cmake: ${source_name} failed (${result})")
endif()