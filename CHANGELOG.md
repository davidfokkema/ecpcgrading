# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Improved handling and activation of uv virtual environments.

## [1.4.0] - 2025-10-10

### Added

- Added details for task errors.

### Changed

- Project is now managed using uv.
- Use uv instead of conda for creating virtual environments.
- A speedrun will also open Visual Studio Code.
- If a student submits a directory, use that as the code directory.

## [1.3.1] - 2024-12-04

### Fixed

- Fix css so "not yet submitted" does not increase height of student widget.

## [1.3.0] - 2024-12-01

### Added

- Config setting "theme" to choose your preferred theme.
- Request submission status with multiple parallel requests, making it much
  faster.

### Changed

- Speedrun no longer opens VS Code automatically. This one's for you, Pim!
- Clicking on a student in the student list will first only highlight the
  student and with a second click select them.

## [1.2.0] - 2024-11-27

### Fixed

- Fix low-chance race condition when the user exits the student view while the
  submission info is still updating.

### Added

- New theming support, courtesy of Textual.
- Show grades in student view.
- Show number of submission comments in student view.
- Show student comments in new screen.

### Changed

- Updated dependencies, new Textual version.
- Removed the 'q' shortcut. Quit is ctrl-c, or accessed through the command
  palette.
- Speedrun now includes the open VS Code task.
- If you select the "grade student" command in the palette, highlight the
  student first and don't immediately jump to the tasks.
- Replaced 'back' bindings with escape instead of 'b' key.

## [1.1.1] - 2024-11-22

### Fixed

- Fix canvas-course-tools dependency.

## [1.1.0] - 2024-11-22

### Added

- Submission status (not yet submitted / on time / time passed deadline) to
  student view.

### Changed

- Match new canvas-course-tools API for submissions.

### Fixed

- Fix crash when an error occurs during speedrun or open VS Code task.

## [1.0.2] - 2024-11-02

### Fixed

- Copy single non-zip, non-bundle files as-is to the code directory. These are
  mostly Python scripts.

## [1.0.1] - 2024-11-01

### Fixed

- Extracting submission from a .bundle no longer fails to check out main branch
  on Windows
- Workaround for environment activation problems on macOS
- Hide git clone output from UI

## [1.0.0] - 2024-10-31

### Added

- When listing all students in a course, include the test student.
- Submitted git .bundle files are recognised and handled correctly.
