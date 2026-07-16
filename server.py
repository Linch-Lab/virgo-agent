#!/usr/bin/env python3
"""Virgo Agent static server with image upload endpoint.
Usage: python3 server.py [port] [directory]
  python3 server.py 8080 /home/virgo
"""
import http.server
import os
import sys
import json
import uuid
import cgi
import io
from pathlib import Path
from urllib.parse import unquote

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
ROOT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
UPLOAD_DIR = ROOT / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB


class VirgoServer(http.server.HTTPServer):
    allow_reuse_address = True


class VirgoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        # Quieter log
        if '/upload' in str(args):
            print(f'  📷 {args[0]}')
        else:
            pass  # suppress static file noise

    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        elif self.path == '/plot':
            self.handle_plot()
        else:
            self.send_error(404, 'POST only supported on /upload and /plot')

    def handle_upload(self):
        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > MAX_SIZE:
            self.send_json({'error': f'File too large (max {MAX_SIZE // 1024 // 1024} MB)'}, 413)
            return

        # Read raw body
        body = self.rfile.read(content_length)

        # Multipart form data
        if 'multipart/form-data' in content_type:
            # Extract boundary
            boundary = content_type.split('boundary=')[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            boundary_bytes = boundary.encode()

            # Parse multipart manually (stdlib cgi is deprecated)
            parts = body.split(b'--' + boundary_bytes)
            for part in parts:
                if b'Content-Disposition' not in part:
                    continue
                # Find the double-CRLF separator between headers and body
                sep = part.find(b'\r\n\r\n')
                if sep == -1:
                    continue
                headers_raw = part[:sep].decode('utf-8', errors='ignore')
                file_data = part[sep + 4:]
                # Remove trailing \r\n before next boundary
                if file_data.endswith(b'\r\n'):
                    file_data = file_data[:-2]

                if not file_data:
                    continue

                # Determine extension from filename or content sniffing
                ext = '.png'
                if 'filename=' in headers_raw:
                    fname = headers_raw.split('filename=')[1].strip().strip('"')
                    ext = Path(fname).suffix.lower() or '.png'

                mime = self.sniff_mime(file_data, ext)
                if mime not in ALLOWED_TYPES:
                    self.send_json({'error': f'Unsupported type: {mime}'}, 415)
                    return

                fname = f'{uuid.uuid4().hex}{ext}'
                filepath = UPLOAD_DIR / fname
                filepath.write_bytes(file_data)

                url = f'/uploads/{fname}'
                self.send_json({'url': url, 'name': fname, 'size': len(file_data)})
                return

            self.send_json({'error': 'No file found in upload'}, 400)
        else:
            # Raw binary upload (e.g., from fetch with blob)
            ext = '.png'
            if 'image/' in content_type:
                ext = '.' + content_type.split('/')[1].split(';')[0]
            fname = f'{uuid.uuid4().hex}{ext}'
            filepath = UPLOAD_DIR / fname
            filepath.write_bytes(body)

            url = f'/uploads/{fname}'
            self.send_json({'url': url, 'name': fname, 'size': len(body)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_plot(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        import numpy as np

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            spec = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({'error': 'Invalid JSON'}, 400)
            return

        plot_type = spec.get('type', 'line')
        data = spec.get('data', {})
        opts = spec.get('options', {})

        # --- Publication-quality style ---
        plt.rcParams.update({
            'font.family': 'serif', 'font.size': 10,
            'axes.labelsize': 11, 'axes.titlesize': 12,
            'xtick.labelsize': 9, 'ytick.labelsize': 9,
            'legend.fontsize': 9, 'figure.dpi': 300,
            'savefig.dpi': 300, 'savefig.bbox': 'tight',
            'axes.linewidth': 1.0, 'axes.spines.top': False,
            'axes.spines.right': False, 'xtick.direction': 'in',
            'ytick.direction': 'in', 'xtick.major.size': 4,
            'ytick.major.size': 4, 'lines.linewidth': 1.5,
        })

        w = opts.get('width', 7)   # inches — 7" for full-width, 3.5" for column
        h = opts.get('height', 4.5)
        fig, ax = plt.subplots(figsize=(w, h))

        labels = data.get('labels', [])
        datasets = data.get('datasets', [])
        colors = ['#2c5f8a', '#b33', '#2a7d4f', '#b8860b', '#8b5cf6', '#e07b39']

        if plot_type in ('line', 'polarization', 'durability'):
            for i, ds in enumerate(datasets):
                x = ds.get('data_x', range(len(labels)))
                y = ds.get('data_y', ds.get('data', []))
                lbl = ds.get('label', f'Series {i+1}')
                c = ds.get('color', colors[i % len(colors)])
                ax.plot(x, y, label=lbl, color=c, marker=ds.get('marker', ''), markersize=3)

        elif plot_type in ('scatter', 'eis'):
            for i, ds in enumerate(datasets):
                x = ds.get('data_x', [])
                y = ds.get('data_y', ds.get('data', []))
                lbl = ds.get('label', f'Series {i+1}')
                c = ds.get('color', colors[i % len(colors)])
                ax.scatter(x, y, label=lbl, color=c, s=12, edgecolors='none')

        elif plot_type == 'bar':
            x = np.arange(len(labels))
            w_bar = 0.8 / max(len(datasets), 1)
            for i, ds in enumerate(datasets):
                y = ds.get('data_y', ds.get('data', []))
                lbl = ds.get('label', f'Series {i+1}')
                c = ds.get('color', colors[i % len(colors)])
                ax.bar(x + i * w_bar, y, w_bar, label=lbl, color=c, edgecolor='white', linewidth=0.5)

        # --- Labels ---
        ax.set_xlabel(opts.get('xlabel', ''))
        ax.set_ylabel(opts.get('ylabel', ''))
        if opts.get('title'):
            ax.set_title(opts['title'], fontweight='bold', pad=10)

        # --- Ticks ---
        if labels and plot_type == 'bar':
            ax.set_xticks(x + w_bar * (len(datasets) - 1) / 2)
            ax.set_xticklabels(labels, rotation=opts.get('xrot', 0), ha='center')
        elif labels and plot_type not in ('scatter', 'eis'):
            ax.set_xticklabels(labels, rotation=opts.get('xrot', 0))

        # --- Legend ---
        if any(ds.get('label') for ds in datasets):
            ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', loc=opts.get('legend_loc', 'best'))

        # --- Grid ---
        if opts.get('grid', True):
            ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)

        # --- Log scale ---
        if opts.get('xlog'):
            ax.set_xscale('log')
        if opts.get('ylog'):
            ax.set_yscale('log')

        # --- Scientific notation on axes ---
        if opts.get('sci_axis'):
            ax.ticklabel_format(axis=opts['sci_axis'], style='sci', scilimits=(-2, 3))

        plt.tight_layout()

        fname = f'{uuid.uuid4().hex}.png'
        filepath = UPLOAD_DIR / fname
        fig.savefig(filepath, dpi=300)
        plt.close(fig)

        url = f'/uploads/{fname}'
        self.send_json({'url': url, 'name': fname})

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def sniff_mime(self, data, ext):
        """Sniff MIME type from magic bytes or extension."""
        if data[:4] == b'\x89PNG':
            return 'image/png'
        if data[:2] == b'\xff\xd8':
            return 'image/jpeg'
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif'
        if data[:4] in (b'RIFF', b'WEBP'):
            return 'image/webp'
        if data[:4] == b'<svg' or data[:5] == b'<?xml':
            return 'image/svg+xml'
        # Fallback by extension
        ext_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                   '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}
        return ext_map.get(ext, 'image/png')


if __name__ == '__main__':
    print(f'  🚀 Virgo Server')
    print(f'     Root:  {ROOT}')
    print(f'     Uploads: {UPLOAD_DIR}')
    print(f'     URL:   http://0.0.0.0:{PORT}')
    print(f'     POST /upload → saves to uploads/')
    print()
    server = VirgoServer(('0.0.0.0', PORT), VirgoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  👋 Shutting down')
        server.server_close()
