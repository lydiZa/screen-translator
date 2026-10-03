# Visual Novel Screen Translator

A lightweight Python desktop utility for real-time OCR and screen translation using Google's Gemini Multimodal API. Designed specifically for reading visual novels and foreign-language games without interrupting your workflow.

The app is a Python desktop translator built around a persistent bounding-box workflow. It uses Tkinter for coordinate overlay mapping, mss for low-latency screen region captures, and threading to run Gemini multimodal API calls in the background so the GUI main loop stays completely responsive. It extracts original dialogue and streams structured translations directly into a customizable, transparent UI.

Tkinter manages the desktop interface, mouse events, and transparent overlays using an event-driven main loop that keeps the UI visible and interactive. mss uses direct OS system calls to capture pixel buffers from your selected screen coordinates in milliseconds without saving files to disk. threading offloads the network API calls to background execution paths so the interface stays fluid and responsive without freezing during text translation.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Gemini API](https://img.shields.io/badge/Google%20Gemini-3.6%20Flash--Lite-8E44AD?style=flat)
---

##  Overview

The app is a Python desktop translator built around a persistent bounding-box workflow. It uses **Tkinter** for coordinate overlay mapping, **`mss`** for low-latency screen region captures, and **`threading`** to run Gemini multimodal API calls in the background so the GUI main loop stays completely responsive. It extracts original dialogue and streams structured translations directly into a customizable, transparent UI.

---

##  Core Architecture & Engineering Highlights

* **Tkinter:** Manages the desktop interface, mouse events, and transparent overlays using an event-driven main loop that keeps the UI visible and interactive.
* **`mss` (Multiple Screen Shots):** Uses direct OS system calls to capture pixel buffers from your selected screen coordinates in milliseconds without saving temporary files to disk.
* **`threading`:** Offloads network API requests to background execution paths so the main interface stays fluid and 60 FPS responsive without freezing during text translation.
* **Gemini 3.6 Flash Integration:** Leverages lightweight multimodal vision processing to optimize for fast response times and minimal token costs per capture.

---

## Features

* **Persistent Bounding Box:** Draw a frame over your game's dialogue box once—the app keeps the active coordinates active until cleared.
* **Hotkey Trigger:** Focus on your game and press `Spacebar` (or click "Capture Next") whenever dialogue changes to fetch instant translations.
* **Dynamic Transparency:** Adjustable opacity slider allows you to overlay the translator window directly over gameplay.
* **Collapsible UI:** Hide or expand the raw OCR dialogue box to save screen real estate.
* **Target Language Selector:** Choose destination languages on the fly from a simple dropdown menu.

---

## Quick Start

### 1. Prerequisites
* Python 3.9 or higher
* A free **Google Gemini API Key** ([Get one here](https://aistudio.google.com/))

### 2. Installation
Clone this repository and install the dependencies:

```bash
git clone [https://github.com/your-username/vn-screen-translator.git](https://github.com/your-username/vn-screen-translator.git)
cd vn-screen-translator
pip install -r requirements.txt
