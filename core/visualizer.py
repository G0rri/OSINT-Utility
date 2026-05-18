import os
import subprocess
import tempfile
from pyvis.network import Network


class NetworkVisualizer:
    """
    Herramienta auxiliar para generar grafos interactivos de relaciones en HTML.
    """

    @staticmethod
    def generate_subdomain_graph(root_domain: str, subdomains: list[str]) -> str:
        """
        Genera un grafo interactivo conectando el dominio raíz con sus subdominios
        y lo guarda en un archivo temporal.
        Retorna la ruta absoluta del archivo generado.
        """
        # cdn_resources='inline' incrusta vis.js completo en el HTML
        # para que funcione correctamente con file:// sin necesidad de internet.
        net = Network(
            height="100vh",
            width="100%",
            bgcolor="#1a1a2e",
            font_color="#e0e0e0",
            cdn_resources="in_line",
        )

        # Nodo central (Root Domain) - Rojo llamativo
        net.add_node(
            root_domain,
            label=root_domain,
            title="<b>🎯 Dominio Raíz</b>",
            color={"background": "#E50914", "border": "#FF4444"},
            size=40,
            shape="diamond",
        )

        # Añadir subdominios y sus aristas
        for sub in subdomains:
            if sub and sub != root_domain:
                net.add_node(
                    sub,
                    label=sub,
                    title=f"<b>Subdominio:</b> {sub}",
                    color={"background": "#1a6db5", "border": "#569CD6"},
                    size=18,
                )
                net.add_edge(root_domain, sub, color="#444466", width=1)

        # Configurar opciones de física para una visualización más rápida y estable
        # Desactivar la física tras la estabilización reduce el tiempo de carga
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "stabilization": {
              "enabled": true,
              "iterations": 150,
              "fit": true
            },
            "barnesHut": {
              "gravitationalConstant": -5000,
              "springLength": 130,
              "springConstant": 0.04,
              "damping": 0.9,
              "avoidOverlap": 0.5
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """)

        # Generar un archivo temporal seguro en /tmp
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".html",
            prefix=f"osint_graph_{root_domain}_",
        )
        file_path = temp_file.name
        temp_file.close()

        net.write_html(file_path)

        # --- Inyectar botón flotante de guardar ---
        save_filename = f"osint_graph_{root_domain}.html"
        save_button_html = f"""
<style>
  #osint-save-btn {{
    position: fixed;
    top: 24px;
    right: 24px;
    z-index: 9999;
    background: linear-gradient(135deg, #1a6db5, #0d4a80);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 15px;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  #osint-save-btn:hover {{
    background: linear-gradient(135deg, #2080d0, #1a5fa0);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(26,109,181,0.6);
  }}
  #osint-save-btn:active {{
    transform: translateY(0);
  }}
</style>
<button id="osint-save-btn" onclick="saveGraph()" title="Guardar grafo como archivo HTML permanente">
  💾 Guardar Grafo
</button>
<script>
function saveGraph() {{
  var html = '<!DOCTYPE html>' + document.documentElement.outerHTML;
  var blob = new Blob([html], {{type: 'text/html;charset=utf-8'}});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = '{save_filename}';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}}
</script>
</body>"""

        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Reemplazar el </body> final para inyectar el botón antes de cerrar
        html_content = html_content.replace("</body>", save_button_html, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path

    @staticmethod
    def open_in_browser(file_path: str):
        """
        Abre un archivo HTML local usando xdg-open para respetar
        el navegador predeterminado del sistema (KDE/GNOME).
        """
        subprocess.Popen(
            ["xdg-open", f"file://{os.path.abspath(file_path)}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
