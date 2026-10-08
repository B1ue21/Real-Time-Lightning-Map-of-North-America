# Live lightning map

A Streamlit app that displays recent NOAA GOES-19 GLM lightning flashes across the contiguous United States. The viewing window is adjustable from 5 to 30 minutes. The map refreshes every 60 seconds while the app is open.

## Add to an existing GitHub repository

1. Extract `lightning-map-github.zip` on your computer.
2. Open your repository on GitHub and choose **Add file > Upload files**.
3. Upload `lightning_map_app.py` and `requirements.txt` together in the same folder, then commit the changes.
4. Optionally include this README and `.gitignore`. If your repository already contains either file, merge the relevant content into the existing file. If it already has a dependency file, merge these dependencies into that file too.

Upload the extracted files, rather than the ZIP itself.

## Run locally

Use Python 3.11 or 3.12. In the folder containing the app, run:

```sh
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Install dependencies and start the app:

```sh
python -m pip install -r requirements.txt
python -m streamlit run lightning_map_app.py
```

## Host on Streamlit Community Cloud

After committing the files to GitHub, create an app at https://share.streamlit.io and select your repository and branch. Set the main file path to `lightning_map_app.py` (or its repository-relative path if you put it in a subfolder). Choose Python 3.11 or 3.12 in the advanced settings.

GitHub stores the source code; a Streamlit host runs the interactive app. GitHub Pages cannot run this Python app.

See the [Streamlit file organization guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization) and [dependency guide](https://docs.streamlit.io/deploy/concepts/dependencies).

## Data and access

The app reads the public `noaa-goes19` AWS bucket using unsigned requests. No AWS credentials or API keys are required. Internet access is needed for NOAA data and the map's geographic assets.

Points represent satellite-detected flashes, including in-cloud lightning. The app reports data lag and file-loading failures. Observations can be delayed or incomplete.

## Validation

This package includes the original app plus its dependency list. Python syntax and dependency coverage were checked during packaging. Live NOAA loading and deployment have not been tested in this packaging environment.
