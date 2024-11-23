# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2024-11-22

### Fixed

- Fix canvas-course-tools dependency.

## [1.1.0] - 2024-11-22

### Added

- Submission status (not yet submitted / on time / time passed deadline) to student view.

### Changed

- Match new canvas-course-tools API for submissions.

### Fixed

- Fix crash when an error occurs during speedrun or open VS Code task.

## [1.0.2] - 2024-11-02

### Fixed

- Copy single non-zip, non-bundle files as-is to the code directory. These are mostly Python scripts.

## [1.0.1] - 2024-11-01

### Fixed

- Extracting submission from a .bundle no longer fails to check out main branch on Windows
- Workaround for environment activation problems on macOS
- Hide git clone output from UI

## [1.0.0] - 2024-10-31

### Added

- When listing all students in a course, include the test student.
- Submitted git .bundle files are recognised and handled correctly.