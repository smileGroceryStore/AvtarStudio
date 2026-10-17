"""Shared quiet dark theme for widget and notification-area native menus."""
import logging
_RENDERER = None
_SOURCE = r"""
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
namespace AvatarStudio.UI {
 public sealed class AvatarMenuRenderer : ToolStripProfessionalRenderer {
  static Color Bg=Color.FromArgb(31,35,41), Line=Color.FromArgb(58,64,73), Accent=Color.FromArgb(111,207,190);
  public AvatarMenuRenderer(){RoundedEdges=false;}
  protected override void OnRenderToolStripBackground(ToolStripRenderEventArgs e){using(var b=new SolidBrush(Bg))e.Graphics.FillRectangle(b,e.AffectedBounds);}
  protected override void OnRenderImageMargin(ToolStripRenderEventArgs e){}
  protected override void OnRenderToolStripBorder(ToolStripRenderEventArgs e){using(var p=new Pen(Line))e.Graphics.DrawRectangle(p,0,0,e.ToolStrip.Width-1,e.ToolStrip.Height-1);}
  protected override void OnRenderMenuItemBackground(ToolStripItemRenderEventArgs e){
   if(!e.Item.Selected || !e.Item.Enabled)return;
   var r=new Rectangle(3,1,e.Item.Width-6,e.Item.Height-2);
   using(var path=new GraphicsPath()) {int d=10;path.AddArc(r.Left,r.Top,d,d,180,90);path.AddArc(r.Right-d,r.Top,d,d,270,90);path.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);path.AddArc(r.Left,r.Bottom-d,d,d,90,90);path.CloseFigure();e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;using(var b=new SolidBrush(Color.FromArgb(49,58,65)))e.Graphics.FillPath(b,path);}
  }
  protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e){
   e.TextColor=!e.Item.Enabled?Color.FromArgb(122,132,144):e.Item.Text.Contains("退出")?Color.FromArgb(245,165,165):Color.FromArgb(232,236,241);base.OnRenderItemText(e);
  }
  protected override void OnRenderSeparator(ToolStripSeparatorRenderEventArgs e){using(var p=new Pen(Line))e.Graphics.DrawLine(p,12,e.Item.Height/2,e.Item.Width-12,e.Item.Height/2);}
  protected override void OnRenderItemCheck(ToolStripItemImageRenderEventArgs e){using(var p=new Pen(Accent,2)){e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;int x=e.ImageRectangle.X+3,y=e.Item.Height/2;e.Graphics.DrawLines(p,new Point[]{new Point(x,y),new Point(x+3,y+3),new Point(x+9,y-4)});}}
  protected override void OnRenderArrow(ToolStripArrowRenderEventArgs e){e.ArrowColor=Accent;base.OnRenderArrow(e);}
 }
}
"""

def apply_menu_theme(menu):
    global _RENDERER
    from System.Drawing import Color, Font, Size
    from System.Windows.Forms import Padding, ToolStripMenuItem
    menu.BackColor=Color.FromArgb(31,35,41)
    menu.ForeColor=Color.FromArgb(232,236,241)
    menu.Font=Font('Microsoft YaHei UI', 10)
    menu.Padding=Padding(5)
    menu.ShowImageMargin=False
    menu.ShowCheckMargin=True
    try:
        if _RENDERER is None:
            import clr
            clr.AddReference('Microsoft.CSharp')
            from Microsoft.CSharp import CSharpCodeProvider
            from System.CodeDom.Compiler import CompilerParameters
            from System import Array, String, Activator
            options=CompilerParameters()
            options.GenerateInMemory=True
            for assembly in ['System.dll','System.Drawing.dll','System.Windows.Forms.dll']:
                options.ReferencedAssemblies.Add(assembly)
            provider=CSharpCodeProvider()
            try:compiled=provider.CompileAssemblyFromSource(options,Array[String]([_SOURCE]))
            finally:provider.Dispose()
            if compiled.Errors.HasErrors:
                raise RuntimeError('; '.join(str(error) for error in compiled.Errors))
            _RENDERER=Activator.CreateInstance(compiled.CompiledAssembly.GetType('AvatarStudio.UI.AvatarMenuRenderer'))
        menu.Renderer=_RENDERER
    except Exception:
        logging.exception('Native menu theme initialization failed')
    for item in menu.Items:
        if isinstance(item, ToolStripMenuItem):
            item.AutoSize=False
            item.Size=Size(256,36)
        else:
            item.AutoSize=False
            item.Size=Size(256,12)
