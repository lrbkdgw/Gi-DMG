cmake_minimum_required(VERSION 3.20)
project(GiDMGNative VERSION 2.2.0 LANGUAGES CXX)

if(NOT WIN32)
  message(FATAL_ERROR "Gi DMG Native is a Windows desktop target. Configure it on Windows with MSVC or MinGW.")
endif()

add_executable(GiDMG WIN32
  src/GiDMG.cpp
  src/model.cpp
)
target_compile_features(GiDMG PRIVATE cxx_std_17)
target_compile_definitions(GiDMG PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(GiDMG PRIVATE user32 gdi32 comctl32 comdlg32 shell32)
if(MSVC)
  target_compile_options(GiDMG PRIVATE /W4 /permissive- /utf-8 /EHsc /Zc:__cplusplus)
  # Static CRT keeps the release a genuinely standalone single EXE.
  set_property(TARGET GiDMG PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
  set_target_properties(GiDMG PROPERTIES LINK_FLAGS "/SUBSYSTEM:WINDOWS")
else()
  target_compile_options(GiDMG PRIVATE -municode -mwindows -Wall -Wextra)
  target_link_options(GiDMG PRIVATE -municode -mwindows -static -static-libgcc -static-libstdc++)
endif()

set_target_properties(GiDMG PROPERTIES OUTPUT_NAME "Gi DMG v2.2.0")
