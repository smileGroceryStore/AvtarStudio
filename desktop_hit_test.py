"""Keep the GPU window intact while making transparent pixels mouse-transparent."""
import logging

_TYPE = None
_SOURCE = r'''
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;
namespace AvatarStudio.UI {
 public sealed class PixelInput : IDisposable {
  [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW")] static extern IntPtr GetStyle(IntPtr h,int n);
  [DllImport("user32.dll",EntryPoint="SetWindowLongPtrW")] static extern IntPtr SetStyle(IntPtr h,int n,IntPtr v);
  [DllImport("user32.dll")] static extern bool SetLayeredWindowAttributes(IntPtr h,uint key,byte alpha,uint flags);
  [DllImport("user32.dll")] static extern short GetAsyncKeyState(int key);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int w,int hgt,uint flags);
  readonly Form form; readonly Timer timer; readonly long original;
  int width,height; string mask=""; bool transparent; Point? probe;
  public bool Transparent {get{return transparent;}}
  public string MaskInfo {get{return width+"x"+height+":"+mask.Length+":"+(mask.Length>0?mask[(height/2)*width+width/2]:'?');}}
  public string StyleInfo {get{return original.ToString("X")+":"+GetStyle(form.Handle,-20).ToInt64().ToString("X");}}
  public PixelInput(Form f){
   form=f; original=GetStyle(f.Handle,-20).ToInt64();
   timer=new Timer();timer.Interval=8;timer.Tick+=(s,e)=>Poll();
   form.FormClosed+=(s,e)=>Dispose();timer.Start();
  }
  public void SetMask(int w,int h,string pixels){width=w;height=h;mask=pixels;Poll();}
  public void Probe(int x,int y){probe=new Point(x,y);Poll();}
  public void ClearProbe(){probe=null;Poll();}
  void Poll(){
   if(form.IsDisposed||!form.IsHandleCreated)return;
   if(!probe.HasValue&&(GetAsyncKeyState(1)<0||GetAsyncKeyState(2)<0||GetAsyncKeyState(4)<0))return;
   Point p=form.PointToClient(probe??Cursor.Position);Size size=form.ClientSize;
   int x=size.Width>0?p.X*width/size.Width:-1,y=size.Height>0?p.Y*height/size.Height:-1;
   bool hit=p.X>=0&&p.Y>=0&&p.X<size.Width&&p.Y<size.Height&&x>=0&&y>=0&&x<width&&y<height&&mask.Length==width*height&&mask[y*width+x]=='1';
   bool next=!hit;if(next==transparent)return;
   long style=GetStyle(form.Handle,-20).ToInt64();
   // WebView GPU surfaces cannot receive input while permanently layered.
   // Enable layered passthrough only over empty pixels; restore normal DWM
   // input on the character. Never use a color key or clip the visible frame.
   SetStyle(form.Handle,-20,new IntPtr(next?style|0x80020L:style&~0x80020L));
   if(next)SetLayeredWindowAttributes(form.Handle,0,255,2);
   SetWindowPos(form.Handle,IntPtr.Zero,0,0,0,0,0x37);
   transparent=next;
  }
  public void Dispose(){timer.Stop();timer.Dispose();}
 }
}
'''

def install_pixel_input(form):
    global _TYPE
    import clr
    clr.AddReference('Microsoft.CSharp')
    from Microsoft.CSharp import CSharpCodeProvider
    from System.CodeDom.Compiler import CompilerParameters
    from System import Array, String, Activator, Object
    if _TYPE is None:
        options = CompilerParameters()
        options.GenerateInMemory = True
        for assembly in ('System.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll'):
            options.ReferencedAssemblies.Add(assembly)
        provider = CSharpCodeProvider()
        try:
            compiled = provider.CompileAssemblyFromSource(options, Array[String]([_SOURCE]))
        finally:
            provider.Dispose()
        if compiled.Errors.HasErrors:
            raise RuntimeError('; '.join(str(error) for error in compiled.Errors))
        _TYPE = compiled.CompiledAssembly.GetType('AvatarStudio.UI.PixelInput')
    return Activator.CreateInstance(_TYPE, Array[Object]([form]))
