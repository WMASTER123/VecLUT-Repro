# This file contains vec-lut-specific compile definitions.

# Set the default options
option(VLUT_AVX512 "Enable AVX512 intrinsics" OFF)
option(VLUT_SVE "Enable SVE intrinsics" OFF)
option(VLUT_ACCELERATE "Enable Accelerate framework on Apple devices" OFF)
option(VLUT_PROFILE "Diagnostic per-phase timers (not for performance results)" OFF)
option(VLUT_I2V4_BLOCKED_WIDEN "Experimental I2_V_4 row-blocked widening transpose" OFF)
option(VLUT_I2V4_SELECTIVE_WIDEN "Experimental shape-guarded I2_V_4 widening" OFF)
if(VLUT_I2V4_BLOCKED_WIDEN AND VLUT_I2V4_SELECTIVE_WIDEN)
    message(FATAL_ERROR "Choose forced or selective widening, not both")
endif()
if(VLUT_I2V4_SELECTIVE_WIDEN)
    add_compile_definitions(VLUT_I2V4_SELECTIVE_WIDEN)
endif()
if(VLUT_I2V4_BLOCKED_WIDEN)
    add_compile_definitions(VLUT_I2V4_BLOCKED_WIDEN)
endif()
if(VLUT_PROFILE)
    if(NOT UNIX)
        message(FATAL_ERROR "VLUT_PROFILE requires a POSIX clock")
    endif()
    add_compile_definitions(VLUT_PROFILE)
endif()

set(TABLE_ENTRY_SIZE 32 CACHE STRING "Tile size of the table entry")
set(WEIGHT_UNROLL_BLOCK 16 CACHE STRING "Weight unroll block size")

# Add compile definitions based on options
add_compile_definitions(TABLE_ENTRY_SIZE=${TABLE_ENTRY_SIZE})
message(STATUS "Adding definition: TABLE_ENTRY_SIZE=${TABLE_ENTRY_SIZE}")

add_compile_definitions(WEIGHT_UNROLL_BLOCK=${WEIGHT_UNROLL_BLOCK})
message(STATUS "Adding definition: WEIGHT_UNROLL_BLOCK=${WEIGHT_UNROLL_BLOCK}")

if(VLUT_AVX512)
    add_compile_definitions(VLUT_AVX512)
    message(STATUS "Adding definition: VLUT_AVX512")
endif()

if(VLUT_SVE)
    add_compile_definitions(VLUT_SVE)
    message(STATUS "Adding definition: VLUT_SVE")
endif()

if(VLUT_ACCELERATE)
    add_compile_definitions(VLUT_ACCELERATE)
    message(STATUS "Adding definition: VLUT_ACCELERATE")
endif()
