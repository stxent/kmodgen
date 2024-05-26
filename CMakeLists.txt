# Copyright (C) 2018 xent
# Project is distributed under the terms of the GNU General Public License v3.0

cmake_minimum_required(VERSION 3.6)
project(kmodgen NONE)

# Build options
set(DESC_DIR "${PROJECT_SOURCE_DIR}/descriptions" CACHE STRING "Path to the description directory.")
set(SPEC_FILE "" CACHE STRING "Path to a custom silkscreen specification file.")
option(USE_PRETTY "Use S-Expression format for footprints." ON)
option(USE_X3D "Use X3D format for package models." ON)

# Build flags for footprint and model generators
set(OUTPUT_DIR ${CMAKE_BINARY_DIR}/lib)
set(FLAGS_FP "")
set(FLAGS_MOD -o ${OUTPUT_DIR})
if(NOT ${SPEC_FILE} STREQUAL "")
    set(FLAGS_FP ${FLAGS_FP} -s ${SPEC_FILE})
endif()
if(USE_PRETTY)
    set(FLAGS_FP ${FLAGS_FP} -o ${CMAKE_BINARY_DIR}/lib)
    install(DIRECTORY ${OUTPUT_DIR}/ DESTINATION ${CMAKE_INSTALL_PREFIX} FILES_MATCHING PATTERN "*.kicad_mod")
else()
    set(FLAGS_FP ${FLAGS_FP} -o ${CMAKE_BINARY_DIR}/obj --legacy)
    install(DIRECTORY ${OUTPUT_DIR}/ DESTINATION ${CMAKE_INSTALL_PREFIX} FILES_MATCHING PATTERN "*.mod")
endif()
if(USE_X3D)
    install(DIRECTORY ${OUTPUT_DIR}/ DESTINATION ${CMAKE_INSTALL_PREFIX} FILES_MATCHING PATTERN "*.x3d")
else()
    set(FLAGS_FP ${FLAGS_FP} --vrml)
    set(FLAGS_MOD ${FLAGS_MOD} --vrml)
    install(DIRECTORY ${OUTPUT_DIR}/ DESTINATION ${CMAKE_INSTALL_PREFIX} FILES_MATCHING PATTERN "*.wrl")
endif()

# List available footprint types
execute_process(
        COMMAND ${PROJECT_SOURCE_DIR}/list_parts.py -f
        RESULT_VARIABLE FOOTPRINT_LIST_RESULT
        OUTPUT_VARIABLE FOOTPRINT_LIST
)
if(NOT ${FOOTPRINT_LIST_RESULT} EQUAL 0)
    message(FATAL_ERROR "Footprint list reading failed")
endif()
string(REGEX REPLACE "\n" ";" FOOTPRINT_LIST "${FOOTPRINT_LIST}")

# List available model types
execute_process(
        COMMAND ${PROJECT_SOURCE_DIR}/list_parts.py -m
        RESULT_VARIABLE MODEL_LIST_RESULT
        OUTPUT_VARIABLE MODEL_LIST
)
if(NOT ${MODEL_LIST_RESULT} EQUAL 0)
    message(FATAL_ERROR "Model list reading failed")
endif()
string(REGEX REPLACE "\n" ";" MODEL_LIST "${MODEL_LIST}")

set(LIB_NAMES "")
file(GLOB_RECURSE DESC_LIST "${DESC_DIR}/*.json")

foreach(DESC_PATH ${DESC_LIST})
    string(REPLACE "${DESC_DIR}/" "" DESC_LIB ${DESC_PATH})
    get_filename_component(DESC_LIB ${DESC_LIB} DIRECTORY)

    list(FIND LIB_NAMES ${DESC_LIB} LIB_NAME_EXISTS)
    if(${LIB_NAME_EXISTS} EQUAL -1)
        list(APPEND LIB_NAMES ${DESC_LIB})
    endif()
endforeach()

foreach(DESC_PATH ${DESC_LIST})
    string(REPLACE "${DESC_DIR}/" "" DESC_LIB ${DESC_PATH})
    get_filename_component(DESC_LIB ${DESC_LIB} DIRECTORY)
    get_filename_component(DESC_FILE ${DESC_PATH} NAME)
    get_filename_component(DESC_NAME ${DESC_FILE} NAME_WE)

    execute_process(
            COMMAND ${PROJECT_SOURCE_DIR}/list_parts.py ${DESC_PATH}
            RESULT_VARIABLE PART_LIST_RESULT
            OUTPUT_VARIABLE PART_LIST
    )
    if(NOT ${PART_LIST_RESULT} EQUAL 0)
        message(FATAL_ERROR "Part list reading failed")
    endif()
    string(REGEX REPLACE "\n" ";" PART_LIST "${PART_LIST}")

    # Generate footprints
    set(FP_LIST "")

    foreach(PART_INFO ${PART_LIST})
        string(REGEX REPLACE "^([^ ]+) ([^ ]+)$" "\\1;\\2" PART_INFO_SPLITTED ${PART_INFO})
        list(GET PART_INFO_SPLITTED 0 PART_TYPE)
        list(GET PART_INFO_SPLITTED 1 PART_NAME)
        list(FIND FOOTPRINT_LIST ${PART_TYPE} TYPE_EXISTS)

        if(NOT ${TYPE_EXISTS} EQUAL -1)
            if(USE_PRETTY)
                set(FP_PATH ${CMAKE_BINARY_DIR}/lib/${DESC_LIB}.pretty/${PART_NAME}.kicad_mod)
            else()
                set(FP_PATH ${CMAKE_BINARY_DIR}/obj/${DESC_LIB}.obj/${PART_NAME}.mod.obj)
            endif()
            set_source_files_properties(${FP_PATH} PROPERTIES GENERATED true)
            add_custom_command(
                    OUTPUT ${FP_PATH}
                    COMMAND ${PROJECT_SOURCE_DIR}/fp.py ${FLAGS_FP} ${DESC_PATH} -l ${DESC_LIB} -f ${PART_NAME}
                    DEPENDS ${DESC_PATH}
            )
            list(APPEND FP_LIST ${FP_PATH})
        endif()
    endforeach()

    list(LENGTH FP_LIST FP_LIST_LENGTH)
    if(${FP_LIST_LENGTH} GREATER 0)
        if(USE_PRETTY)
            add_custom_target(${DESC_NAME}_fp ALL SOURCES ${FP_LIST})
            message(STATUS "Library ${DESC_LIB}: added footprints from ${DESC_FILE}")
        else()
            set(${DESC_LIB}_SOURCES ${${DESC_LIB}_SOURCES} ${FP_LIST})
        endif()
    endif()

    # Generate 3D models
    set(MOD_LIST "")

    foreach(PART_INFO ${PART_LIST})
        string(REGEX REPLACE "^([^ ]+) ([^ ]+)$" "\\1;\\2" PART_INFO_SPLITTED ${PART_INFO})
        list(GET PART_INFO_SPLITTED 0 PART_TYPE)
        list(GET PART_INFO_SPLITTED 1 PART_NAME)
        list(FIND MODEL_LIST ${PART_TYPE} TYPE_EXISTS)

        if(NOT ${TYPE_EXISTS} EQUAL -1)
            if(USE_X3D)
                set(MOD_PATH ${OUTPUT_DIR}/${DESC_LIB}/${PART_NAME}.x3d)
            else()
                set(MOD_PATH ${OUTPUT_DIR}/${DESC_LIB}/${PART_NAME}.wrl)
            endif()
            list(APPEND MOD_LIST ${MOD_PATH})
            set_source_files_properties(${MOD_PATH} PROPERTIES GENERATED true)
            add_custom_command(
                    OUTPUT ${MOD_PATH}
                    COMMAND ${PROJECT_SOURCE_DIR}/mod.py ${FLAGS_MOD} ${DESC_PATH} -l ${DESC_LIB} -f ${PART_NAME}
                    DEPENDS ${DESC_PATH}
            )
        endif()
    endforeach()

    list(LENGTH MOD_LIST MOD_LIST_LENGTH)
    if(${MOD_LIST_LENGTH} GREATER 0)
        add_custom_target(${DESC_NAME}_mod ALL SOURCES ${MOD_LIST})
        message(STATUS "Library ${DESC_LIB}: added models from ${DESC_FILE}")
    endif()
endforeach()

if(NOT USE_PRETTY)
    foreach(LIB_NAME ${LIB_NAMES})
        list(LENGTH ${LIB_NAME}_SOURCES FP_LIST_LENGTH)
        if(${FP_LIST_LENGTH} GREATER 0)
            set(FP_LIB_PATH ${OUTPUT_DIR}/${LIB_NAME}.mod)
            set_source_files_properties(${FP_LIB_PATH} PROPERTIES GENERATED true)
            add_custom_command(
                    OUTPUT ${FP_LIB_PATH}
                    COMMAND ${PROJECT_SOURCE_DIR}/archive_parts.py -l ${FP_LIB_PATH} ${${LIB_NAME}_SOURCES}
                    DEPENDS ${${LIB_NAME}_SOURCES}
            )
            add_custom_target(${LIB_NAME}_fp ALL SOURCES ${FP_LIB_PATH})
            message(STATUS "Library ${LIB_NAME}: added footprints")
        endif()
    endforeach()
endif()
