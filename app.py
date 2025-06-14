import keyword
from flask import Flask, request, render_template, send_file, send_from_directory
import os
import PyPDF2
from openai import OpenAI, api_key
from werkzeug.utils import secure_filename
import openai
from openai import OpenAI
import re
from pdf2image import convert_from_path
from inference import run_inference_and_save_images
from api_call import get_bounding_boxes, draw_bounding_boxes, format_object_counts, count_objects
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
app = Flask(__name__)
client = None  # Will be initialized after app config
# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
EXTRACTED_FOLDER = 'extracted'
ALLOWED_EXTENSIONS = {'pdf'}
IMAGES_FOLDER = 'images'



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXTRACTED_FOLDER'] = EXTRACTED_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
# Create necessary folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
import PyPDF2

# Function to find pages with target keywords and convert them to images
def find_and_convert_pages_to_images(pdf_path):
    target_keywords = ['PLAN - LIGHTING', 'REFLECTED CEILING', 'FLOOR PLAN - POWER', 'EP1.1', 'Architectural Floor Plan', 'AE1.01', 'FLOOR PLAN -POWER']
    found_pages = {}
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            print(f"Page {i+1} text: {text[:100]}...")  # Print first 100 characters for context
            for keyword in target_keywords:
                if keyword.lower() in text.lower():
                    # Convert the identified page to an image
                    image_path = convert_page_to_image(pdf_path, i)
                    found_pages[keyword] = image_path
                    print(f"Found keyword '{keyword}' on page {i+1}")
                    break

    return found_pages

# Note: Make sure convert_page_to_image function is defined correctly.
# Function to convert a specified page of a PDF to an image
# Function to convert a specified page of a PDF to an image
from PIL import Image, ImageOps

# Function to convert a specified page of a PDF to an image
def convert_page_to_image(pdf_path, page_number):
    # Convert specific page to image using pdf2image
    images = convert_from_path(pdf_path, first_page=page_number+1, last_page=page_number+1, dpi=200)
    image_filename = f'page_{page_number + 1}.png'
    image_path = os.path.join(app.config['IMAGES_FOLDER'], image_filename)
    
    # Save the image
    images[0].save(image_path, 'PNG')
    
    return image_filename


@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['IMAGES_FOLDER'], filename)





# Function to search for electrical indicators in a PDF and extract pages
# Function to search for electrical indicators in a PDF and extract pages
def extract_electrical_pages(pdf_path):
    keywords = ['ELECTRICAL DETAILS', 'FLOOR PLAN - LIGHTING', 'JUNCTION BOX', 'SWITCHES', 'DUPLEX', 'DECORA', 'RECEPTICLE', 'CONTACTOR', 'EXIT SIGN', 'EMERGENCY LIGHT', 'FLOOR PLAN - POWER', 'E0.01', 'EL1.1', 'EP1.1', 'E2.0', 'E3.0', 'EP1.1', 'WATER HEATERS', 'INSTAHOT', 'VAV', 'FAN POWERED BOX']
    # keywords = ['ELECTRICAL DETAILS']
    
    extracted_pages = []
    

    # Open the PDF file
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # Check for electrical keywords in the page text
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    print(f"Keyword '{keyword}' found on page {i + 1}")  # Print keyword and page number
                    extracted_pages.append(i)
                    break  # Exit the loop once a keyword is found to avoid duplicate entries for the same page

    # Extract the identified pages to a new PDF
    if extracted_pages:
        extracted_pdf_path = os.path.join(app.config['EXTRACTED_FOLDER'], 'extracted_electrical_pages.pdf')
        writer = PyPDF2.PdfWriter()
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in extracted_pages:
                try:
                    # Attempt to add the page and catch any errors
                    writer.add_page(reader.pages[page_num])
                except Exception as e:
                    print(f"Failed to add page {page_num}: {e}")
            # Only write to the file if there are pages successfully added
            if writer.pages:
                with open(extracted_pdf_path, 'wb') as output_file:
                    writer.write(output_file)
                return extracted_pdf_path, extracted_pages
            else:
                return None, []
    else:
        return None, []
page_title_pattern = re.compile(r'\b[A-Z]+\d{1,2}\.\d{2}\b')
# Function to extract text from the extracted PDF with page titles
def extract_text_with_page_titles(pdf_path):
    pages_text = {}
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # Find the page title using the regular expression
            page_title_match = page_title_pattern.search(text)
            if page_title_match:
                page_title = page_title_match.group(0)
                pages_text[page_title] = text.strip()
            else:
                # If no title is found, use the page number as a fallback
                pages_text[f"Page {i+1}"] = text.strip()
    return pages_text

# Function to send text to an LLM for summarization
def summarize_text_with_llm(text_by_page, api_key):
      # Set your OpenAI API key here
    formatted_text = "\n\n".join(
    f"Page Title: {page_title}\n{text}" for page_title, text in text_by_page.items()
    )
    print(f"Formatted text before encode: {formatted_text}")  # Print first 500 characters for debugging
    print(f"Formatted text after encode: {formatted_text}")
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                "content": (
                    "You are an electrician's assistant. Your task is to review the provided project documents and summarize all the important electrical information that an electrician would need to know to complete this project. "
                    "Please be as detailed as possible and organize the summary into sections."
                    "Do not mention details that are not related to electrical work. Only focus on electrical details.\n\n"
                    "Provide the page that each detail can be found on(E01.1, A2.1, etc)" 
                    "Some of the important electrical items may include:" 
                    "- Name of the job\n"
                    "- address of the job\n"
                    "- most recent addendum(if any) and the date of the most recent addendum\n" 
                    "- number of outlets\n" 
                    "- outlet height\n"
                    "- outlet type\n"
                    "- outlet color\n"
                    "- any specialty outlets\n"
                    "- a list of all the lights and their model numbers/details\n"
                    "- quantity of each type of light\n"
                    "- new or reused lights/exit signs?\n"
                    "- will the lights need to be dimmable?\n"
                    "- does the print call for lighting controls? If so, what kind?\n"
                    "- a list of any water heaters, instahots, HVAC units, VAVs, Fan Powered Boxes and their power requirements\n"
                    "- A list of all electrical equipment to be installed (e.g., panels, disconnects, transformers, generators)\n"
                    "- Any specialized equipment or circuits (e.g., dedicated circuits for appliances, HVAC systems).\n"
                    "- Furniture or architectural features that involve electrical connections (e.g., furniture feeds, built-in outlets).\n\n"
                    # "1. **Outlet Details**:\n"
                    # "   - Expected height of outlets and over-counter outlets.\n"
                    # "   - Type of outlets specified (e.g., standard, Decora, GFCI).\n"
                    # "   - Color or style of outlets (e.g., white, almond).\n"
                    # "   - Locations where dedicated, tamper-resistant or weather-resistant outlets are required.\n"
                    # "   - Quantity of 20-amp, 15-amp, and USB outlets.\n\n"
                   
                    
                    # "2. **Lighting Information**:\n"
                    # "   - Types of lights to be installed (e.g., LED, fluorescent, recessed, track lighting).\n"
                    # "   - Light fixture specifications (e.g., wattage, color temperature, voltage).\n"
                    # "   - Any dimmer switches or lighting controls specified.\n"
                    # "   - Locations and mounting heights of light fixtures.\n"
                    # "   - Quantity of light fixtures and their locations.\n\n"
                    
                    # "3. **Power and Equipment Requirements**:\n"
                    # "   - A list of all electrical equipment to be installed (e.g., panels, disconnects, transformers, generators).\n"
                    # "   - Any specialized equipment or circuits (e.g., dedicated circuits for appliances, HVAC systems).\n"
                    # "   - Details about emergency power availability or requirements for battery backups.\n\n"
                    
                    # "4. **Ceiling and Wall Information**:\n"
                    # "   - Ceiling height throughout the space.\n"
                    # "   - Any ceiling or wall materials that could affect installation (e.g., concrete, drywall).\n"
                    # "   - Locations where fixtures need to be mounted on suspended ceilings.\n\n"
                    
                    # "5. **Reuse of Existing Materials**:\n"
                    # "   - List any materials or equipment specified to be reused (e.g., existing light fixtures, conduit).\n"
                    # "   - Details about any existing infrastructure that should remain unchanged.\n\n"
                    
                    # "6. **Conduit, Wiring, and Cable Specifications**:\n"
                    # "   - Types and sizes of conduit to be used (e.g., EMT, PVC).\n"
                    # "   - Wire sizes, types, and insulation ratings (e.g., THHN, Romex).\n"
                    # "   - Any special cable requirements (e.g., shielded cables, fiber optics).\n"
                    # "   - Raceway and cable tray details, if mentioned.\n\n"
                    
                    # "7. **Safety and Compliance Information**:\n"
                    # "   - Any grounding and bonding requirements.\n"
                    # "   - Location of emergency shutoffs or disconnects.\n\nd"
                                        
                    # "8. **Miscellaneous**:\n"
                   # "   - Power requirements of instahots, water heaters, or HVAC equipment.\n"               
                    # "   - Any unique or project-specific notes that could impact installation (e.g., specific timelines, coordination with other trades).\n"
                    # "   - Furniture or architectural features that involve electrical connections (e.g., furniture feeds, built-in outlets).\n\n"
                    
                    "Please summarize the information in a clear and organized manner, focusing on what an electrician needs to know to execute the project successfully."
                )},
                {"role": "user", "content": formatted_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error while calling the LLM API: {e}")
        return "Failed to summarize the text."



import markdown2
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return "No file part in the request"
        file = request.files['file']
        if file.filename == '':
            return "No file selected for uploading"
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Use the hardcoded API key from the configuration
            api_key = app.config['OPENAI_API_KEY']

            # Analyze the PDF for electrical pages
            extracted_pdf_path, pages_found = extract_electrical_pages(file_path)

            # Find "Reflected Ceiling" and "Architectural Floor Plan" pages and convert them to images
            image_paths = find_and_convert_pages_to_images(file_path)
            output_image_paths = run_inference_and_save_images(image_paths)
            object_counts = {}

            annotated_image_paths = {}
            for keyword, output_image_path in output_image_paths.items():
                full_image_path = os.path.join(app.config['IMAGES_FOLDER'], output_image_path)
                bounding_boxes = get_bounding_boxes(full_image_path)

                if bounding_boxes:
                    # Update the object count
                    counts = count_objects(bounding_boxes)
                    for category, count in counts.items():
                        if category in object_counts:
                            object_counts[category] += count
                        else:
                            object_counts[category] = count

                    # Draw bounding boxes on the images
                    annotated_image_path = draw_bounding_boxes(full_image_path, bounding_boxes)
                    annotated_image_paths[f"{keyword} Annotated"] = os.path.basename(annotated_image_path)
                else:
                    print(f"Failed to get bounding boxes for {output_image_path}")

            # Format the object counts as a string
            object_counts_str = format_object_counts(object_counts)

            summary = None
            if extracted_pdf_path:
                # Extract text from the extracted PDF with page titles
                text_content = extract_text_with_page_titles(extracted_pdf_path)

                if text_content:
                    # Prepend the object counts to the text content, robustly handling None values
                    for page_title in list(text_content.keys()):
                        page_text = text_content.get(page_title)
                        if not isinstance(page_text, str):
                            print(f"[ERROR] page_text for '{page_title}' is type {type(page_text)} or is None. Replacing with empty string.")
                            page_text = ""
                        text_content[page_title] = (object_counts_str or "") + "\n" + page_text
                    summary_markdown = summarize_text_with_llm(text_content, api_key)
                    # Convert Markdown to HTML
                    summary = markdown2.markdown(summary_markdown)

            # Render the result.html template with all relevant information
            return render_template(
                'result.html',
                pages=pages_found,
                file_path=extracted_pdf_path,
                summary=summary,
                image_paths=annotated_image_paths
            )

    return render_template('upload.html')

@app.route('/download')
def download_file():
    file_path = request.args.get('file_path')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found."

# HTML templates
UPLOAD_HTML = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload PDF</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #2c2c2c;
            color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            background-color: #3a3a3a;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            margin: 50px auto;
            text-align: center;
        }
        h1 {
            color: #00aaff;
        }
        p, label {
            color: #cccccc;
        }
        .form-group {
            margin: 20px 0;
        }
        input[type="file"] {
            width: 100%;
            padding: 10px;
            margin-top: 8px;
            border-radius: 5px;
            border: 1px solid #555;
            box-sizing: border-box;
            background-color: #555;
            color: #f0f0f0;
        }
        input[type="submit"] {
            background-color: #00aaff;
            color: #ffffff;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        input[type="submit"]:hover {
            background-color: #0088cc;
        }
        .instructions {
            background-color: #444;
            padding: 15px;
            border-radius: 5px;
            text-align: left;
            margin-top: 20px;
        }
        .loading-message {
            display: none;
            color: #00aaff;
            margin-top: 20px;
            font-size: 18px;
        }
    </style>
    <script>
        function showLoadingMessage() {
            document.getElementById("loading-message").style.display = "block";
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Upload a PDF</h1>
        <p>Welcome to our PDF Analysis Tool! This site allows you to upload a PDF containing architectural and electrical plans. The system will automatically detect and extract relevant electrical pages, analyze the content, and highlight important features such as annotated images with bounding boxes.</p>
        <div class="instructions">
            <h2>Instructions:</h2>
            <ol>
                <li>Select a PDF file from your computer. Make sure the file is relevant to architectural or electrical plans.</li>
                <li>Click the "Upload" button to submit the PDF for analysis.</li>
                <li>Once the analysis is complete, you will see a summary of the extracted content and annotated images highlighting important features.</li>
            </ol>
            <p>Supported file format: <strong>PDF (.pdf)</strong></p>
        </div>
        <form method="post" enctype="multipart/form-data" onsubmit="showLoadingMessage()">
            <div class="form-group">
                <label for="file">Choose PDF File:</label>
                <input type="file" name="file" id="file" accept=".pdf" required>
            </div>
            <div class="form-group">
                <input type="submit" value="Upload">
            </div>
        </form>
        <div id="loading-message" class="loading-message">
            Please wait patiently while your print is being analyzed. This may take a minute or two...
        </div>
    </div>
</body>
</html>
'''

RESULT_HTML = '''
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Result</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #2c2c2c;
            color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            background-color: #3a3a3a;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 800px;
            margin: 50px auto;
            text-align: left;
        }
        h1, h2, h3 {
            color: #00aaff;
        }
        p, pre, ul, ol {
            color: #cccccc;
            text-align: left; /* Align paragraphs and lists to the left */
            line-height: 1.6;
        }
        pre {
            background-color: #444;
            padding: 15px;
            border-radius: 5px;
            text-align: left;
            overflow-x: auto;
        }
        ul, ol {
        padding-left: 40px; /* Add padding to the left for lists */
        }
        li {
            margin-bottom: 8px; /* Add some space between list items */
        }
        img {
            max-width: 100%;
            height: auto;
            border: 1px solid #777;
            border-radius: 5px;
            margin-top: 20px;
        }
        .go-back {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 15px;
            background-color: #00aaff;
            color: #ffffff;
            text-decoration: none;
            border-radius: 5px;
        }
        .go-back:hover {
            background-color: #0088cc;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Result</h1>

        <!-- Display the extracted pages information -->
        <h2>Extracted Electrical Pages:</h2>
        {% if pages %}
            <p>Pages with electrical content found: {{ pages }}</p>
        {% else %}
            <p>No electrical pages were found in the PDF.</p>
        {% endif %}

        <!-- Display the summary of extracted text -->
        <h2>Summary of Extracted Text:</h2>
        {% if summary %}
            <div>{{ summary | safe }}</div>
        {% else %}
            <p>No text could be extracted or summarized.</p>
        {% endif %}

        <h2>Annotated Images with Bounding Boxes:</h2>
        {% if image_paths %}
            {% for label, image_path in image_paths.items() %}
                <div>
                    <h3>{{ label }}</h3>
                    <img src="{{ url_for('serve_image', filename=image_path) }}" alt="{{ label }}">
                </div>
            {% endfor %}
        {% else %}
            <p>No annotated images available.</p>
        {% endif %}

        <br><a href="/" class="go-back">Go back to upload</a>
    </div>
</body>
</html>
'''

# Create the HTML templates
with open('templates/upload.html', 'w') as f:
    f.write(UPLOAD_HTML)

with open('templates/result.html', 'w') as f:
    f.write(RESULT_HTML)

if __name__ == '__main__':
    client = OpenAI(api_key=app.config['OPENAI_API_KEY'])  # Initialize client with API key
    app.run(debug=True, host='0.0.0.0')