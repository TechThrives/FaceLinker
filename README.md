# FaceLinker
Effortlessly Organize and Analyze Event Photos with Advanced Facial Recognition

## Overview
FaceLinker is an advanced image processing and facial recognition application designed to streamline the organization and analysis of event photos. With FaceLinker, users can:

- Upload multiple images from various events.
- Extract faces from these images.
- Group similar faces together for easy organization and analysis.

## Features

- **Bulk Image Upload:** Upload multiple images from different events for batch processing.
- **Facial Extraction:** Automatically detect and extract faces from uploaded images.
- **Face Grouping:** Organize photos by grouping similar faces together.
- **Event Management:** Keep your event photos organized by categorizing them into different events.

## Tech Stack

**Frontend:** HTML, Tailwind, JavaScript 

**Backend:** Python Flask

**Database:** MongoDB

**Facial Recognition:** DeepFace

**Image Storage:** Supabase

## Installation
To get started with FaceLinker, follow these steps:

Prerequisites
- Python installed on your machine.
- MongoDB installed and running.
- Supabase account and project set up.

### Clone the project

```bash
git clone https://github.com/yourusername/FaceLinker.git
```

Go to the project directory

```bash
cd FaceLinker
```

### Install Dependencies
Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`SECRET_KEY`

`MONGO_URI`

`SUPABASE_URL`

`SUPABASE_KEY`

`SUPABASE_BUCKET`

## Start the Application

```bash
flask run
```

The application will be available at http://localhost:5000.

## Demo

https://github.com/user-attachments/assets/25b751b4-d94e-4911-b037-f293759363a0

## Contributing
Contributions are welcome! Please follow these steps:

- Fork the repository.
- Create a new branch (`git checkout -b feature/your-feature-name`).
- Commit your changes (`git commit -m 'Add some feature'`).
- Push to the branch (`git push origin feature/your-feature-name`).
- Open a Pull Request.

## Contact

For any questions or suggestions, please feel free to contact us.
