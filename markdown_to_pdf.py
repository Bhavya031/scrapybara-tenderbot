# tender_report.py
from markdown import Markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import os
from datetime import datetime


def format_tender_report(tenders, client_name):
    """
    Format tender data into markdown text
    """
    markdown_text = f"""# Tender Report for {client_name}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Available Tenders

"""
    for tender in tenders:
        markdown_text += f"""### {tender['title']}
- **Tender ID**: {tender.get('tender_id', 'N/A')}
- **Bid Deadline**: {tender.get('deadline', 'N/A')}
- **Estimated Value**: {tender.get('value', 'N/A')}

**Description**:
{tender.get('description', 'No description available')}

---
"""

    return markdown_text


def create_tender_pdf(markdown_text, output_path):
    """
    Convert tender report markdown to PDF
    """
    try:
        md = Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'smarty'
        ])

        html = md.convert(markdown_text)

        css = '''
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
            
            body {
                font-family: 'Inter', sans-serif;
                line-height: 1.4;
                max-width: 800px;
                margin: 0 auto;
                padding: 1em;
                color: #333;
            }
            
            h1 {
                color: #1a365d;
                font-size: 1.8em;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 0.3em;
                margin-bottom: 1em;
            }
            
            h2 {
                color: #2d3748;
                font-size: 1.5em;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            
            h3 {
                color: #4a5568;
                font-size: 1.2em;
                margin-top: 1em;
                margin-bottom: 0.5em;
            }
            
            p {
                margin: 0.5em 0;
            }
            
            ul {
                margin: 0.5em 0;
                padding-left: 1.5em;
            }
            
            li {
                margin: 0.2em 0;
            }
            
            strong {
                color: #2d3748;
            }
            
            hr {
                border: none;
                border-top: 1px solid #e2e8f0;
                margin: 1em 0;
            }
            
            @page {
                margin: 2cm;
                @bottom-right {
                    content: counter(page);
                    font-size: 0.9em;
                    color: #718096;
                }
            }
        '''

        full_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Tender Report</title>
        </head>
        <body>
            {html}
        </body>
        </html>
        '''

        font_config = FontConfiguration()

        HTML(string=full_html).write_pdf(
            output_path,
            stylesheets=[CSS(string=css, font_config=font_config)],
            font_config=font_config
        )

        return output_path

    except Exception as e:
        print(f"Error creating PDF: {e}")
        raise
