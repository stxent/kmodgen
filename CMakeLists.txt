# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

project(kmodgen NONE)
cmake_minimum_required(VERSION 3.6)
cmake_policy(SET CMP0054 NEW)

# Build options
set(SPEC_FILE "" CACHE STRING "Path to a custom spec file.")
option(USE_PRETTY "Use S-Expression format for footprints." ON)
option(USE_X3D "Use X3D format for package models." ON)

set(FLAGS_FP -o ${CMAKE_BINARY_DIR}/lib)
set(FLAGS_MOD -o ${CMAKE_BINARY_DIR}/lib)
if(NOT ${SPEC_FILE} STREQUAL "")
    set(FLAGS_FP ${FLAGS_FP} -s ${SPEC_FILE})
endif()
if(${USE_PRETTY})
    set(FLAGS_FP ${FLAGS_FP} -p)
endif()
if(${USE_X3D})
    set(FLAGS_FP ${FLAGS_FP} -f x3d)
    set(FLAGS_MOD ${FLAGS_MOD} -f x3d)
else()
    set(FLAGS_FP ${FLAGS_FP} -f wrl)
    set(FLAGS_MOD ${FLAGS_MOD} -f wrl)
endif()

file(GLOB DESC_LIST "${PROJECT_SOURCE_DIR}/descriptions/*.json")

foreach(DESC_PATH ${DESC_LIST})
    get_filename_component(DESC_NAME ${DESC_PATH} NAME)
    get_filename_component(DESC_NAME ${DESC_NAME} NAME_WE)

    add_custom_target(${DESC_NAME}_fp ALL DEPENDS ${DESC_PATH})
    add_custom_command(TARGET ${DESC_NAME}_fp COMMAND ${PROJECT_SOURCE_DIR}/fp.py ${FLAGS_FP} -i ${DESC_PATH})

    add_custom_target(${DESC_NAME}_mod ALL DEPENDS ${DESC_PATH})
    add_custom_command(TARGET ${DESC_NAME}_mod COMMAND ${PROJECT_SOURCE_DIR}/mod.py ${FLAGS_MOD} -i ${DESC_PATH})
endforeach()

install(DIRECTORY ${CMAKE_BINARY_DIR}/lib/ DESTINATION ${CMAKE_INSTALL_PREFIX}
        FILES_MATCHING PATTERN "*.kicad_mod" PATTERN "*.mod" PATTERN "*.wrl" PATTERN "*.x3d")
