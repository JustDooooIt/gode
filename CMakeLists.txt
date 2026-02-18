cmake_minimum_required(VERSION 3.12)
project(gode)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Use C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# -----------------------------------------------------------------------------
# Godot-CPP
# -----------------------------------------------------------------------------

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/godot-cpp/CMakeLists.txt")
    message(FATAL_ERROR "godot-cpp submodule not found! Please initialize it.")
endif()

# Add godot-cpp as a subdirectory
add_subdirectory(godot-cpp)

# -----------------------------------------------------------------------------
# Node-Addon-API & LibNode
# -----------------------------------------------------------------------------

# Path to node-addon-api (header-only wrapper for N-API)
set(NODE_ADDON_API_DIR "${CMAKE_CURRENT_SOURCE_DIR}/node-addon-api")

if(NOT EXISTS "${NODE_ADDON_API_DIR}/napi.h")
    message(WARNING "node-addon-api headers not found at ${NODE_ADDON_API_DIR}. Please check path.")
endif()

# Path to Node.js source or install
# If using source, we need headers from src, deps/v8/include, deps/uv/include
set(NODE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/node")
set(NODE_INCLUDE_DIRS
    "${NODE_ROOT}/src"
    "${NODE_ROOT}/deps/v8/include"
    "${NODE_ROOT}/deps/uv/include"
)

# Try to find libnode library
# On Windows, we look for node.lib
if(WIN32)
    # Common locations for prebuilt node.lib or build artifacts
    # You might need to adjust this path or pass -DNODE_LIBRARY=path/to/node.lib
    find_library(NODE_LIBRARY NAMES node libnode
        PATHS
        "${NODE_ROOT}/out/Release"
        "${NODE_ROOT}/out/Debug"
        NO_DEFAULT_PATH
    )
    if(NOT NODE_LIBRARY)
        find_library(NODE_LIBRARY NAMES node libnode
            PATHS
            "C:/Program Files/nodejs"
            DOC "Path to node.lib"
        )
    endif()
else()
    # On Linux/macOS
    find_library(NODE_LIBRARY NAMES node libnode
        PATHS
        "/usr/local/lib"
        "${NODE_ROOT}/out/Release"
    )
endif()

if(NOT NODE_LIBRARY)
    message(WARNING "libnode library not found. Linking might fail. Please set NODE_LIBRARY manually using -DNODE_LIBRARY=path/to/libnode.")
endif()

#
# -----------------------------------------------------------------------------
# Target: gode
# -----------------------------------------------------------------------------

file(GLOB_RECURSE GODE_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
)

add_library(gode SHARED ${GODE_SOURCES})

target_include_directories(gode PRIVATE
    include 
    ${NODE_ADDON_API_DIR}
    ${NODE_INCLUDE_DIRS}
)

# Preprocessor definitions
target_compile_definitions(gode PRIVATE
    NAPI_VERSION=8          # Set N-API version
    # NAPI_CPP_EXCEPTIONS   # Enable/Disable C++ exceptions for N-API
)

target_link_libraries(gode
    godot::cpp
)

if(NODE_LIBRARY)
    target_link_libraries(gode ${NODE_LIBRARY})
    
    # Try to find the corresponding DLL
    get_filename_component(NODE_LIB_DIR "${NODE_LIBRARY}" DIRECTORY)
    find_file(NODE_DLL NAMES libnode.dll node.dll
        PATHS "${NODE_LIB_DIR}"
        NO_DEFAULT_PATH
    )
    
    if(NODE_DLL)
        message(STATUS "Found Node.js DLL: ${NODE_DLL}")
        add_custom_command(TARGET gode POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${NODE_DLL}"
                "${CMAKE_SOURCE_DIR}/example/addons/gode/bin"
        )
    else()
        message(WARNING "Could not find node.dll or libnode.dll in ${NODE_LIB_DIR}. You may need to copy it manually.")
    endif()
endif()

add_custom_command(TARGET gode POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory
        "${CMAKE_SOURCE_DIR}/example/addons/gode/bin"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:gode>
        "${CMAKE_SOURCE_DIR}/example/addons/gode/bin/libgode.dll"
)
