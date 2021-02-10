##   Copyright (C) 2010 University of Texas at Austin
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2 of the License, or
##   (at your option) any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.
##
##   You should have received a copy of the GNU General Public License
##   along with this program; if not, write to the Free Software
##   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
'''
   how do you write selfdoc for m8r?
'''

import os, sys, tempfile, re, subprocess, urllib, datetime
import numpy as np

import rsf.doc
import rsf.prog
import rsf.path

try:
    import c_m8r as c_rsf
    _swig_ = True
except:
    _swig_ = False

python2 = sys.version_info[0] < 3
    
def view(name):
    'for use in Jupyter notebooks'
    try:
        from IPython.display import Image
        png = name+'.png'
        makefile = os.path.join(rsf.prog.RSFROOT,'include','Makefile')
        os.system('make -f %s %s' % (makefile,png))
        return Image(filename=png)
    except:
        print ('No IPython Image support')
        return None

class _Simtab(dict):
    'simbol table (emulates api/c/simtab.c)'
    def __init__(self):
        dict.__init__(self)
    def enter(self,key,val):
        'add key=val to the table'
        self[key] = val
    def getint(self,key):
        val = self.get(key)
        if val:
            return True,int(val)
        return False,None
    def getints(self,key,n):
        val = self.get(key)
        if val:
            vals = val.split(',')
            nval = len(vals)
            # set array to length n
            if n < nval:
                vals = vals[:n]
            elif n > nval:
                vals.extend((n-nval)*[vals[nval-1]])
            return True,[int(v) for v in vals]
        return False,None
    def getfloat(self,key):
        val = self.get(key)
        if val:
            return True,float(val)
        return False,None
    def getfloats(self,key,n):
        val = self.get(key)
        if val:
            vals = val.split(',')
            nval = len(vals)
            # set array to length n
            if n < nval:
                vals = vals[:n]
            elif n > nval:
                vals.extend((n-nval)*[vals[nval-1]])
            return True,[float(v) for v in vals]
        return False,None
    def getstring(self,key):
        val = self.get(key)
        if None == val:
            return None
        # strip quotes
        if val[0] == '"' and val[-1] == '"':
            val = val[1:-1]
        return val
    def getbool(self,key):
        val = self.get(key)
        if val:
            if val[0] == 'y' or val[0] == 'Y' or val[0] == '1':
                return True,True
        else:
            return True,False
        return False,None
    def getbools(self,key,n):
        val = self.get(key)
        if val:
            vals = val.split(',')
            nval = len(vals)
            # set array to length n
            if n < nval:
                vals = vals[:n]
            elif n > nval:
                vals.extend((n-nval)*[vals[nval-1]])
            bools = []
            for val in vals:
                bools.append(val[0] == 'y' or val[0] == 'Y' or val[0] == '1')
            return True,bools
        return False,None
    def put(self,keyval):
        if '=' in keyval:
            key,val = keyval.split('=')
            self.enter(key,val)
    def string(self,string):
        'extract parameters from a string'
        for word in string.split():
            self.put(word)
    def input(self,filep,out=None):
        'extract parameters from header file'
        while True:
            try:
                if python2:
                    line3 = filep.read(3)
                else:
                    line3 = filep.buffer.read(3)
                # skip new lines
                while line3[:1] == b'\n':
                    if python2:
                        line3 = line3[1:] + filep.read(1)
                    else:
                        line3 = line3[1:] + filep.buffer.read(1)
                # check code for the header end
                if line3 == b'\x0c\x0c\x04':
                    break
                if python2:
                    line = line3+filep.readline()
                else:
                    line = str(line3+filep.buffer.readline(),'utf-8')
                if len(line) < 1:
                    break
                if out:
                    out.write(line)
                self.string(line)
            except:
                break
        if out:
            out.flush()
    def output(self,filep):
        'output parameters to a file'
        for key in self.keys():
            filep.write('\t%s=%s\n' % (key,self[key]))
 
class Par(object):
    '''command-line parameter table'''
    def __init__(self,argv=sys.argv):
        global par
        # c_rsf.sf_init needs 'utf-8' (bytes) not unicode
        if _swig_:
            c_rsf.sf_init(len(argv),
                            [arg.encode('utf-8') for arg in argv])
            self.prog = c_rsf.sf_getprog()
        else:
            self.pars = _Simtab()
            self.prog = argv[0]
            
            for arg in argv[1:]:
                if arg[:4] == 'par=':
                    parfile = open(arg[4:],'r')
                    self.pars.input(parfile)
                    parfile.close()
                else:
                    self.pars.put(arg)
            
        for type in ('int','float','bool'):
            setattr(self,type,self.__get(type))
            setattr(self,type+'s',self.__gets(type))
        par = self
    def getprog(self):
        return self.prog
    def __get(self,type):
        if _swig_:
            func = getattr(c_rsf,'sf_get'+type)
        else:
            func = getattr(self.pars,'get'+type)
        def _get(key,default=None):
            if python2:
                # c function only knows utf-8 (ascii).  translate the unicode
                key = key.encode('utf-8')
            get,par = func(key)
            if get:
                return par
            elif default != None:
                return default
            else:
                return None
        return _get
    def __gets(self,type):
        if _swig_:
            func = getattr(c_rsf,'get'+type+'s')
        else:
            func = getattr(self.pars,'get'+type)
        def _gets(key,num,default=None):
            pars = func(key,num)
            if pars:
                return pars
            elif default:
                return default
            else:
                return None
        return _gets
    def string(self,key,default=None):        
        if _swig_:
            if python2:
                # c function only knows utf-8 (ascii).  translate the unicode
                key = key.encode('utf-8')
            val = c_rsf.sf_getstring(key)
        else:
            val = self.pars.getstring(key)
    
        if val:
            return val
        elif default:
            return default
        else:
            return None

par = Par(['python','-'])

def no_swig():
    'disable swig for testing'
    global _swig_, par
    _swig_ = False
    par = Par(['python','-'])
        
class Temp(str):
    'Temporaty file name'
    datapath = rsf.path.datapath()
    tmpdatapath = os.environ.get('TMPDATAPATH',datapath)
    def __new__(cls):
        return str.__new__(cls,tempfile.mktemp(dir=Temp.tmpdatapath))

class File(object):
    'generic RSF file object'
    attrs = ['rms','mean','norm','var','std','max','min','nonzero','samples']
    def __init__(self,tag,temp=False,name=''):
        'Constructor'
        self.temp = temp
        if isinstance(tag,File):
            # copy file (name is ignored)
            self.__init__(tag.tag)
            tag.close()
        elif isinstance(tag,np.ndarray):
            # numpy array
            dtype = tag.dtype
            if dtype=='float32':
                dformat='native_float'
            elif dtype=='int32':
                 dformat='native_int'
            else:
                print('Unsupported format',dtype,file=sys.stderr)
                sys.exit(12)
            if not name:
                name = Temp()
            out = Output(name,data_format=dformat)
            shape = tag.shape
            dims = len(shape)
            for axis in range(1,dims+1):
                out.put('n%d' % axis,shape[dims-axis])
            out.write(tag)
            out.close()
            self.__init__(out,temp=True)
        elif isinstance(tag,list):
            self.__init__(np.array(tag,'f'),name)
        else:
            self.tag = tag
        self.filename=self.tag
        self.narray = []
        for filt in Filter.plots + Filter.diagnostic:
            # run things like file.grey() or file.sfin()
            setattr(self,filt,Filter(filt,srcs=[self],run=True))
        for attr in File.attrs:
            setattr(self,attr,self.want(attr))
    def __str__(self):
        'String representation'
        if self.tag:
            tag = str(self.tag)
            if os.path.isfile(tag):
                return tag
            else:
                raise TypeError('Cannot find "%s" ' % tag)
        else:
            raise TypeError('Cannot find tag')
    def sfin(self):
        'Output of sfin'
        return Filter('in',run=True)(0,self)
    def want(self,attr):
        'Attributes from sfattr'
        def wantattr():
            try:
                val = os.popen('%s want=%s < %s' %
                               (Filter('attr'),attr,self)).read()
            except:
                raise RuntimeError('trouble running sfattr')
            m = re.search('=\s*(\S+)',val)
            if m:
                val = float(m.group(1))
            else:
                raise RuntimeError('no match')
            return val
        return wantattr
    def real(self):
        'Take real part'
        re = Filter('real')
        return re[self]
    def cmplx(self,im):
        c = Filter('cmplx')
        return c[self,im]
    def imag(self):
        'Take imaginary part'
        im = Filter('imag')
        return im[self]
    def __add__(self,other):
        'Overload addition'
        add = Filter('add')
        return add[self,other]
    def __sub__(self,other):
        'Overload subtraction'
        sub = Filter('add')(scale=[1,-1])
        return sub[self,other]
    def __mul__(self,other):
        'Overload multiplication'
        try:
            mul = Filter('scale')(dscale=float(other))
            return mul[self]
        except:
            mul = Filter('mul')(mode='product')
            return mul[self,other]
    def __div__(self,other):
        'Overload division'
        try:
            div = Filter('scale')(dscale=1.0/float(other))
            return div[self]
        except:
            div = Filter('add')(mode='divide')
            return div[self,other]
    def __neg__(self):
        neg = Filter('scale')(dscale=-1.0)
        return neg[self]
    def dot(self,other):
        'Dot product'
        # incorrect for complex numbers
        prod = self.__mul__(other)
        stack = Filter('stack')(norm=False,axis=0)[prod]
        return stack[0]
    def cdot2(self):
        'Dot product with itself'
        stack = Filter('math')(output="\"input*conj(input)\"").real.stack(norm=False,axis=0)[self]
        return stack[0]
    def dot2(self):
        'Dot product with itself'
        return self.dot(self)
    def __array__(self,context=None):
        'create narray'
        if [] == self.narray:
            if _swig_:
                if not hasattr(self,'file'):
                    f = c_rsf.sf_input(self.tag)
                else:
                    f = self.file
                self.narray = c_rsf.rsf_array(f)
                if not hasattr(self,'file'):
                    c_rsf.sf_fileclose(f)
            else:
                # gets only the real part of complex arrays ##kls
                if not hasattr(self,'file'):
                    f=Input(self.filename)
                else:
                    f=self.file
                self.narray=np.memmap(f.string('in'),dtype=f.datatype,
                                      mode='r+',
                                      shape=f.shape())
        return self.narray
    def __array_wrap__(self,array,context=None):
        inp = Input(self)
        inp.read(array)
        return inp
    def __getitem__(self,i):
        array = self.__array__()
        return array[i]
    def __setitem__(self,index,value):
        array = self.__array__()
        array.__setitem__(index,value)
    def size(self,dim=0):
        return File.leftsize(self,dim)

    def leftsize(self,dim=0):
        if _swig_:
            if hasattr(self,'file'):
                f = self.file
            else:
                f = c_rsf.sf_input(self.tag)
            s = c_rsf.sf_leftsize(f,dim)
            if not hasattr(self,'file'):
                c_rsf.sf_fileclose(f)
            return s
        else:
            s = 1
            for axis in range(dim+1,10):
                n = self.int("n%d" % axis)
                if n:
                    s *= n
                else:
                    break
            return s
    def int(self,key,default=None):
        get = self.get(key)
        if get:
            val = int(get)
        elif default:
            val = default
        else:
            val = None
        return val
    def float(self,key,default=None):
        get = self.get(key)
        if get:
            val = float(get)
        elif default:
            val = default
        else:
            val = None
        return val
    def get(self,key):
        'returns a string'
        try:
            p = subprocess.Popen('%s %s parform=n < %s' %
                                 (Filter('get'),key,self),
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 close_fds=True)
            result = p.stdout.read()
        except:
            raise RuntimeError('trouble running sfget')
        return result
    def shape(self):
        # axes are reversed for consistency with numpy
        s = []
        dim = 1
        for i in range(1,10):
            ni = self.int('n%d' % i)
            if ni:
                dim = i
            s.append(ni)
        s = s[:dim]
        # the trailing members of s that are 1 ie fix situations like
        # s=(1500,240,1,1)
        while s[-1]==1 and len(s)>1:
            s=s[:-1]
        s.reverse()
        return tuple(s)
    def reshape(self,shape=None):
        if not shape:
            shape = self.size()
        try:
            shape = list(shape)
        except:
            shape = [shape]
        old = list(self.shape())
        old.reverse()
        shape.reverse()
        lold = len(old)
        lshape = len(shape)
        puts = {}
        for i in range(max(lold,lshape)):
            ni = 'n%d' % (i+1)
            if i < lold:
                if i < lshape:
                    if old[i] != shape[i]:
                        puts[ni] = shape[i]
                else:
                    puts[ni] = 1
            else:
                puts[ni] = shape[i]
        put = Filter('put')
        put.setcommand(puts)
        return put[self]
    def __len__(self):
        return self.size()
    def __del__(self):
        # remove temporary files
        if hasattr(self,'temp') and self.temp:
            Filter('rm',run=True)(0,self)

class _File(File):
    types = ['uchar','char','int','float','complex']
    forms = ['ascii','xdr','native']
    def __init__(self,tag):
        if not self.file:
            raise TypeError('Use Input or Output instead of File')
        if _swig_:
            self.type = _File.types[c_rsf.sf_gettype(self.file)]
            self.form = _File.forms[c_rsf.sf_getform(self.file)]
        else:
            self.type = self.file.gettype()
            self.form = self.file.getform()
        if self.type=='float':
            self.datatype=np.float32
        elif self.type=='complex':
            self.datatype=np.complex64
        elif self.type=='int':
            self.datatype=np.int32
        else:
            sys.stderr.write('unsupported type\n')
            sys.exit(1)
        File.__init__(self,tag)
 
    def tell(self):
        if _swig_:
            return c_rsf.sf_tell(self.file)
        else:
            return self.file.tell()
    def close(self):
        if _swig_:
            c_rsf.sf_fileclose(self.file)
        else:
            self.file.fileclose()
    def __del__(self):
        if self.file:
            if _swig_:
                c_rsf.sf_fileclose(self.file)
            else:
                self.file.fileclose()
        File.__del__(self) # this removes file if it is temporary
    def settype(self,type):
        if _swig_:
            for i in range(len(_File.type)):
                if type == _File.type[i]:
                    self.type = type
                    c_rsf.sf_settype(self.file,i)
                    break
        else:
            self.file.settype(type)
            self.type = type
    def setformat(self,format):
        if _swig_:
            c_rsf.sf_setformat(self.file,format)
        else:
            self.file.setformat(format)
    def __get(self,func,key,default):
        if _swig_:
            get,par = func(self.file,key)
        else:
            get,par = func(key)
        if get:
            return par
        elif default:
            return default
        else:
            return None
    def __gets(self,func,key,num,default):
        if _swig_:
            pars = func(self.file,key,num)
        else:
            pars = func(key,num)
        if pars:
            return pars
        elif default:
            return default
        else:
            return None
    def string(self,key):
        if _swig_:
            return c_rsf.sf_histstring(self.file,key)
        else:
            return self.file.string(key)
    def int(self,key,default=None):
        if _swig_:
            return self.__get(c_rsf.sf_histint,key,default)
        else:
            return self.__get(self.file.int,key,default)
    def float(self,key,default=None):
        if _swig_:
            return self.__get(c_rsf.sf_histfloat,key,default)
        else:
            return self.__get(self.file.float,key,default)
    def ints(self,key,num,default=None):
        if _swig_:
            return self.__gets(c_rsf.histints,key,num,default)
        else:
            return self.__gets(self.file.ints,key,num,default)
    def bytes(self):
        if _swig_:
            return c_rsf.sf_bytes(self.file)
        else:
            return self.file.bytes()
    def put(self,key,val):
        if _swig_:
            if isinstance(val,int):
                c_rsf.sf_putint(self.file,key,val)
            elif isinstance(val,float):
                c_rsf.sf_putfloat(self.file,key,val)
            elif isinstance(val,str):
                c_rsf.sf_putstring(self.file,key,val)
            elif isinstance(val,list):
                if isinstance(val[0],int):
                    c_rsf.sf_putints(self.file,key,val)
        else:
            if isinstance(val,int):
                self.file.putint(key,val)
            elif isinstance(val,float):
                self.file.putfloat(key,val)
            elif isinstance(val,str):
                self.file.putstring(key,val)
            elif isinstance(val,list):
                if isinstance(val[0],int):
                    self.file.putints(key,val)
    def axis(self,i):
        ax = {}
        ax['n'] = self.int("n%d"   % i)
        ax['d'] = self.float("d%d" % i)
        ax['o'] = self.float("o%d" % i)
        ax['l'] = self.string("label%d" % i)
        ax['u'] = self.string("unit%d" % i)
        return ax
    def putaxis(self,ax,i):
        self.put("n%d" % i,ax['n'])
        self.put("d%d" % i,ax['d'])
        self.put("o%d" % i,ax['o'])
        if ax['l']:
            self.put("label%d" % i,ax['l'])
        if ax['u']:
            self.put("unit%d" % i,ax['u'])

class Input(_File):
    '''
    RSF file for reading.  
    '''
    def __init__(self,tag='in'):
        self.file = None
        if isinstance(tag,File):
            # copy file
            self.__init__(tag.tag)
        else:
            if _swig_:
                self.file = c_rsf.sf_input(tag)
            else:
                self.file = _RSF(True,tag)
        _File.__init__(self,tag)
    def read(self,data=[],shape=None,datatype=None):
        if len(data) == 0:
            allocate = True
            if shape==None:
                shape=self.shape()
            if datatype==None:
                datatype=self.datatype
            data=np.zeros(shape,dtype=datatype)
        else:
            allocate = False
        shape=data.shape
        datacount=data.size
        if _swig_:
            if self.type == 'float':
                c_rsf.sf_floatread(np.reshape(data,(data.size,)),self.file)
            elif self.type == 'complex':
                c_rsf.sf_complexread(np.reshape(data,(data.size)),self.file)
            elif self.type == 'int':
                c_rsf.sf_intread(np.reshape(data,(data.size,)),self.file)
            else:
                raise TypeError('Unsupported file type %s' % self.type)
        else:
            if self.type == 'float':
                self.file.floatread(np.reshape(data,(data.size,)))
            elif self.type == 'int':
                self.file.intread(np.reshape(data,(data.size,)))
            else:
                raise TypeError('Unsupported file type %s' % self.type)
        if allocate:
            return data
            
class Output(_File):
    def __init__(self,tag='out',data_format=None):
        self.file = None
        if _swig_:
            self.file = c_rsf.sf_output(tag)
        else:
            self.file = _RSF(False,tag)
            if data_format:
                self.file.setformat(data_format)
        _File.__init__(self,tag)
    def write(self,data):
        if _swig_:
            if self.type == 'float':
                c_rsf.sf_floatwrite(np.reshape(data.astype(np.float32),(data.size,)),self.file)
            elif self.type == 'complex':
                c_rsf.sf_complexwrite(np.reshape(data,(data.size,)),
                                      self.file)
            elif self.type == 'int':
                c_rsf.sf_intwrite(np.reshape(data.astype(np.int32),(data.size,)),self.file)
            else:
                raise TypeError('Unsupported file type %s' % self.type)
        else:
            if self.type == 'float':
                self.file.floatwrite(np.reshape(data.astype(np.float32),(data.size,)))
            elif self.type == 'int':
                self.type.intwrite(np.reshape(data.astype(np.int32),(data.size,)))
            else:
                raise TypeError('Unsupported file type %s' % self.type)
                
dataserver = os.environ.get('RSF_DATASERVER',
                            'http://www.reproducibility.org')

def Fetch(directory,filename,server=dataserver,top='data'):
    'retrieve a file from remote server'
    if server == 'local':
        remote = os.path.join(top,
                            directory,os.path.basename(filename))
        try:
            os.symlink(remote,filename)
        except:
            print ('Could not link file "%s" ' % remote)
            os.unlink(filename)
    else:
        rdir =  os.path.join(server,top,
                             directory,os.path.basename(filename))
        try:
            urllib.urlretrieve(rdir,filename)
        except:
            try:
                urllib.request.urlretrieve(rdir,filename)
            except:
                print ('Could not retrieve file "%s" from "%s"' % (filename,rdir))

class Filter(object):
    'Madagascar filter'
    plots = ('grey','contour','graph','contour3',
             'dots','graph3','thplot','wiggle','grey3')
    diagnostic = ('attr','disfil','headerattr')
    def __init__(self,name,prefix='sf',srcs=[],
                 run=False,checkpar=False,pipe=False):
        rsfroot = rsf.prog.RSFROOT
        self.plot = False
        self.stdout = True
        self.prog = None
        if rsfroot:
            lp = len(prefix)
            if name[:lp] != prefix:
                name = prefix+name
            self.prog = rsf.doc.progs.get(name)
            prog = os.path.join(rsfroot,'bin',name)
            if os.path.isfile(prog):
                self.plot   = name[lp:] in Filter.plots
                self.stdout = name[lp:] not in Filter.diagnostic
                name = prog
        self.srcs = srcs
        self.run=run
        self.command = name
        self.checkpar = checkpar
        self.pipe = pipe
        if self.prog:
            self.__doc__ =  self.prog.text(None)

    def getdoc():
        '''for IPython'''
        return self.__doc__
    def _sage_argspec_():
        '''for Sage'''
        return None
    def __wrapped__():
        '''for IPython'''
        return None
    def __str__(self):
        return self.command
    def __or__(self,other):
        'pipe overload'
        self.command = '%s | %s' % (self,other)
        return self
    def setcommand(self,kw,args=[]):
        parstr = []
        for (key,val) in kw.items():
            if key[:2] == '__': # convention to handle -- parameters
                key = '--'+key[2:]
            if self.checkpar and self.prog and not self.prog.pars.get(key):
                sys.stderr.write('checkpar: No %s= parameter in %s\n' %
                                 (key,self.prog.name))
            if isinstance(val,str):
                val = '\''+val+'\''
            elif isinstance(val,File):
                val = '\'%s\'' % val
            elif isinstance(val,bool):
                if val:
                    val = 'y'
                else:
                    val = 'n'
            elif isinstance(val,list):
                val = ','.join(map(str,val))
            else:
                val = str(val)
            parstr.append('='.join([key,val]))
        self.command = ' '.join([self.command,
                                 ' '.join(map(str,args)),
                                 ' '.join(parstr)])
    def __getitem__(self,srcs):
        'Apply to data'
        mysrcs = self.srcs[:]
        if isinstance(srcs,tuple):
            mysrcs.extend(srcs)
        elif isinstance(srcs,np.ndarray) or srcs:
            mysrcs.append(srcs)

        if self.stdout:
            if isinstance(self.stdout,str):
                out = self.stdout
            else:
                out = Temp()
            command = '%s > %s' % (self.command,out)
        else:
            command = self.command

        (first,pipe,second) = command.partition('|')

        numpy = False
        for n, src in enumerate(mysrcs):
            if isinstance(src,np.ndarray):
                mysrcs[n] = File(src)
                numpy = True

        if mysrcs:
            command = ' '.join(['< ',str(mysrcs[0]),first]+
                                list(map(str,list(mysrcs[1:]))) +
                               [pipe,second])

        fail = os.system(command)
        if fail:
            raise RuntimeError('Could not run "%s" ' % command)

        if self.stdout:
            if self.plot:
                return Vplot(out,temp=True)
            else:
                outfile = File(out,temp=True)
                if numpy:
                    return outfile[:]
                else:
                    return outfile
    def __call__(self,*args,**kw):
        if args:
            self.stdout = args[0]
            self.run = True
        elif not kw and not self.pipe:
            self.run = True
        self.setcommand(kw,args[1:])
        if self.run:
            return self[0]
        else:
            return self
    def __getattr__(self,attr):
        'Making pipes'
        other = Filter(attr)
        self.pipe = True
        self.command = '%s | %s' % (self,other)
        return self

def Vppen(plots,args):
    name = Temp()
    os.system('vppen %s %s > %s' % (args,' '.join(map(str,plots)),name))
    return Vplot(name,temp=True)

def Overlay(*plots):
    return Vppen(plots,'erase=o vpstyle=n')

def Movie(*plots):
    return Vppen(plots,'vpstyle=n')

def SideBySide(*plots,**kw):
    n = len(plots)
    iso = kw.get('iso')
    if iso:
        return Vppen(plots,'size=r vpstyle=n gridnum=%d,1' % n)
    else:
        return Vppen(plots,'yscale=%d vpstyle=n gridnum=%d,1' % (n,n))

def OverUnder(*plots,**kw):
    n = len(plots)
    iso = kw.get('iso')
    if iso:
        return Vppen(plots,'size=r vpstyle=n gridnum=1,%d' % n)
    else:
        return Vppen(plots,'xscale=%d vpstyle=n gridnum=1,%d' % (n,n))

class Vplot(object):
    def __init__(self,name,temp=False,penopts=''):
        'Constructor'
        self.name = name
        self.temp = temp
        self.img = None
        self.penopts = penopts+' '
    def __del__(self):
        'Destructor'
        if self.temp:
            try:
                os.unlink(self.name)
            except:
                raise RuntimeError('Could not remove "%s" ' % self)
    def __str__(self):
        return self.name
    def __mul__(self,other):
        return Overlay(self,other)
    def __add__(self,other):
        return Movie(self,other)
    def show(self):
        'Show on screen'
        os.system('sfpen %s' % self.name)
    def hard(self,printer='printer'):
        'Send to printer'
        os.system('PRINTER=%s pspen %s' % (printer,self.name))
    def image(self):
        'Convert to PNG in the current directory (for use with IPython and SAGE)'
        self.img = os.path.basename(self.name)+'.png'
        self.export(self.img,'png',args='bgcolor=w')
    def _repr_png_(self):
        'return PNG representation'
        if not self.img:
            self.image()
        img = open(self.img,'rb')
        guts = img.read()
        img.close()
        return guts

    try:
        from IPython.display import Image

        @property
        def png(self):
            return Image(self._repr_png_(), embed=True)
    except:
        pass

    def movie(self):
        'Convert to animated GIF in the current directory (for use with SAGE)'
        self.gif = os.path.basename(self.name)+'.gif'
        self.export(self.gif,'gif',args='bgcolor=w')
    def export(self,name,format=None,pen=None,args=''):
        'Export to different formats'
        from rsf.vpconvert import convert
        if not format:
            if len(name) > 3:
                format = name[-3:].lower()
            else:
                format = 'vpl'
        convert(self.name,name,format,pen,self.penopts+args,verb=False)

class _Wrap(object):
    'helper class to wrap all Madagascar programs as Filter objects'
    def __init__(self, wrapped):
        self.wrapped = wrapped
    def __getattr__(self, name):
        try:
            return getattr(self.wrapped, name)
        except AttributeError:
            if name in rsf.doc.progs.keys() or \
              'sf'+name in rsf.doc.progs.keys():
                return Filter(name)
            else:
                raise

sys.modules[__name__] = _Wrap(sys.modules[__name__])

# Helper classes for the case of no SWIG

little_endian = (sys.byteorder == 'little')
    
class _RSF(object):
    'rsf file (emulates api/c/file.c)'
    infiles = [None]
    def __init__(self,input,tag=None):
        global par
        self.pars = _Simtab()
        for type in ('int','float','bool'):
            setattr(self,type, getattr(self.pars,'get'+type))
            setattr(self,type+'s',getattr(self.pars,'get'+type+'s'))
        if input: # input file
            # set data stream
            if tag==None or tag=='in':
                self.stream = sys.stdin
                filename = None
            else:
                filename = par.string(tag)
                if filename==None:
                    filename = tag
                self.stream = open(filename,'r+')
            # temporary file for header
            self.headname = Temp() 
            self.head = open(self.headname,'w+')
            # read parameters
            self.pars.input(self.stream,self.head)
            # keep track of input files
            global infiles
            if filename==None:
                _RSF.infiles[0] = self
            else:
                _RSF.infiles.append(self)
            # get dataname
            filename = self.string('in')
            if filename==None:
                self.input_error('No in= in file',tag)
            self.dataname = filename
            # keep stream in the special case of in=stdin
            if filename != 'stdin':
                self.stream = open(filename,'r+b')
                
            # set format
            data_format = self.string('data_format')
            if not data_format:
                data_format = 'ascii_format'
            self.setformat(data_format)
        else: # output file
            if tag==None or tag=='out':
                self.stream = sys.stdout
                headname = None
            else:
                headname = par.string(tag)
                if headname==None:
                    headname = tag
                self.stream = open(headname,'w+')
            self.headname = None
            # check if piping
            try:
                t = self.stream.tell()
                self.pipe = False
            except:
                self.pipe = True
            if self.stream == sys.stdout:
                dataname = par.string('--out') or par.string('out')
            else:
                dataname = None
            if self.pipe:
                self.dataname = 'stdout'
            elif dataname==None:
                path = rsf.path.datapath()
                name = self.getfilename()
                if name != None:
                    if name=='/dev/null':
                        self.dataname = 'stdout'
                    else:
                        self.dataname = os.path.join(path,name+'@')
                else:
                    # invent a name
                    self.dataname = Temp()
            else:
                self.dataname = dataname

            self.putstring('in',self.dataname)

            if None != _RSF.infiles[0]:
                format = _RSF.infiles[0].string('data_format','native_float')
                self.setformat(format)

            self.rw = par.bool('--readwrite',False)
            self.dryrun = par.bool('--dryrun',False)                    
    def input_error(self,message,name):
        print(message,name,file=sys.stderr)
        sys.exit(1)
    def getfilename(self):
        'find the name of the file to which we are writing'
        found_stdout = False

        f = '/dev/null'
        if os.fstat(1)[1] == os.stat(f)[1]:
            found_stdout = True
        else:        
            for f in os.listdir('.'):
                # Comparing the unique file ID stored by the OS for the file stream
                # stdout with the known entries in the file table:
                if os.path.isfile(f) and os.fstat(1)[1] == os.stat(f)[1]:
                    found_stdout = True
                    break

        if found_stdout:
            return f
        else:
            return None
    def gettype(self):
        return self.type
    def getform(self):
        return self.form
    def settype(self,type):
        self.type = type
    def setform(self,form):
        self.form = form
        if form == 'ascii':
            if None != self.dataname:
                self.put('esize',0) # for compatibility with SEPlib
            self.aformat = None
            self.eformat = None
            self.aline = 8
    def setformat(self,dataformat):
        done = False
        for type in ('float','int','complex','uchar','short','long','double'):
            if type in dataformat:
                self.settype(type)
                done = True
                break
        if not done:
            if 'byte' in dataformat:
                self.settype('uchar')
            else:
                self.settype('char')
        if dataformat[:6]=='ascii_':
            self.setform('ascii')
        elif dataformat[:4]=='xdr_':
            self.setform('xdr')
        else:
            self.setform('native')
    def string(self,key,default=None):
        get = self.pars.getstring(key)
        if get:
            return get
        else:
            return default
    def fileflush(self,src):
        import pwd, socket, time
        if None==self.dataname:
            return
        if None != src and None != src.head:
            src.head.seek(0)
            for line in src.head:
                self.stream.write(line)

        user = os.getuid()
        username = pwd.getpwuid(user)[0]
        self.stream.write("%s\t%s:\t%s@%s\t%s\n" % \
                       (par.getprog(),
                         os.getcwd(),
                        username,
                        socket.gethostname(),
                        time.ctime()))
        self.putstring('data_format','_'.join([self.form,self.type]))
        self.pars.output(self.stream)
        self.stream.flush()

        if self.dataname == 'stdout':
            # keep stream, write the header end code
            self.stream.write('\tin="stdin"\n\n\x0c\x0c\x04')
            self.stream.flush()
        else:                   
            self.stream = open(self.dataname,'w+b')

        self.dataname = None
        if self.dryrun:
            sys.exit(0)
    def fflush(self):
        self.stream.flush()
    def putint(self,key,par):
        if None==self.dataname:
            print('putint to a closed file',file=sys.stderr)
            sys.exit(1)
        val = '%d' % par
        self.pars.enter(key,val)
    def putints(self,key,par,n):
        if None==self.dataname:
            print('putints to a closed file',file=sys.stderr)
        sys.exit(1)
        val = ''
        for i in range(n-1):
            val += '%d,' % par[i]
        val += '%d' % par[n-1]
        self.pars.enter(key,val)
    def putfloat(self,key,par):
        if None==self.dataname:
            print('putfloat to a closed file',file=sys.stderr)
            sys.exit(1)
        val = '%g' % par
        self.pars.enter(key,val)
    def putfloats(self,key,par,n):
        if None==self.dataname:
            print('putfloats to a closed file',file=sys.stderr)
            sys.exit(1)
        val = ''
        for i in range(n-1):
            val += '%g,' % par[i]
        val += '%g' % par[n-1]
        self.pars.enter(key,val)
    def putstring(self,key,par):
        if None==self.dataname:
            print('putstring to a closed file',file=sys.stderr)
            sys.exit(1)
        val = '\"%s\"' % par
        self.pars.enter(key,val)
    def intwrite(self,arr):
        if None != self.dataname:
            self.fileflush(_RSF.infiles[0])
                
        if self.form=='ascii':
            if self.aformat == None:
                aformat = '%d '
            else:
                aformat = self.aformat
            if self.eformat == None:
                eformat = '%d '
            else:
                eformat = self.aformat
            size = arr.size
            farr = arr.flatten()
            left = size    
            while left > 0:
                if self.aline < left:
                    nbuf = self.aline
                else:
                    nbuf = left
                last = size-left+nbuf-1
                for i in range(size-left,last):
                    self.stream.write(aformat % farr[i])
                self.stream.write(eformat % farr[last])
                self.stream.write("\n")
                left -= nbuf
        else:
            try:
                self.stream.buffer.write(arr.tobytes())
            except:
                if python2:
                    self.stream.write(arr.tostring())
                else:
                    self.stream.write(arr.tobytes())
    def intread(self,arr):
        if self.form=='ascii':
            arr[:] = np.loadtxt(self.stream,dtype='int32',count=arr.size)
        else:
            try:
                data = self.stream.buffer.read(arr.size*4)
            except:
                data = self.stream.read(arr.size*4)
                if not python2 and type(data) == str:
                    data = data.encode()
            arr[:] = np.frombuffer(data,dtype='int32')
    def floatwrite(self,arr):
        if None != self.dataname:
            self.fileflush(_RSF.infiles[0])
                
        if self.form=='ascii':
            if self.aformat == None:
                aformat = '%g '
            else:
                aformat = self.aformat
            if self.eformat == None:
                eformat = '%g '
            else:
                eformat = self.aformat
            size = arr.size
            farr = arr.flatten()
            left = size    
            while left > 0:
                if self.aline < left:
                    nbuf = self.aline
                else:
                    nbuf = left
                last = size-left+nbuf-1
                for i in range(size-left,last):
                    self.stream.write(aformat % farr[i])
                self.stream.write(eformat % farr[last])
                self.stream.write("\n")
                left -= nbuf
        else:
            try:
                self.stream.buffer.write(arr.tobytes())
            except:
                if python2:
                    self.stream.write(arr.tostring())
                else:
                    self.stream.write(arr.tobytes())
    def floatread(self,arr):
        if self.form=='ascii':
            arr[:] = np.loadtxt(self.stream,dtype='float32',count=arr.size)
        else:
            try:
                data = self.stream.buffer.read(arr.size*4)
            except:
                data = self.stream.read(arr.size*4)
                if not python2 and type(data) == str:
                    data = data.encode()
            arr[:] = np.frombuffer(data,dtype='float32')
    def tell(self):
        return self.stream.tell()
    def bytes(self):
        if self.dataname=='stdin':
            return -1
        if self.dataname==None:
            st = os.fstat(self.stream.fileno())
        else:
            st = os.stat(self.dataname)
        return st.st_size
    def fileclose(self):
        if self.stream != sys.stdin and \
          self.stream != sys.stdout and \
          self.stream != None:
            self.stream.close()
            self.stream = None
        if self.headname != None:
            os.unlink(self.headname)
            self.headname = None


if __name__ == "__main__":

#      a=100 Xa=5
#      float=5.625 cc=fgsg
#      dd=1,2x4.0,2.25 true=yes false=2*no label="Time (sec)"
   
#    no_swig()
    # Testing getpar
    par = Par(["prog","a=5","b=as","a=100","float=5.625",
               "true=y"]) #,"par=%s" % sys.argv[0]])
    assert 100 == par.int("a")
    assert not par.int("c")
    assert 10 == par.int("c",10)
    assert 5.625 == par.float("float")
    assert par.bool("true")
    #assert "Time (sec)" == par.string("label")
    #assert "Time (sec)" == par.string("label","Depth")
    assert not par.string("nolabel")
    assert "Depth" == par.string("nolabel","Depth")
    # no function for this   par.close()
    # Testing file
    # Redirect input and output
    inp = os.popen("sfspike n1=100 d1=0.25 nsp=2 k1=1,10 label1='Time'")
    out = open("junk.rsf","w")
    os.dup2(inp.fileno(),sys.stdin.fileno())
    os.dup2(out.fileno(),sys.stdout.fileno())
    # Initialize
    par = Par()
    input = Input()
    output = Output()
    # Test
    assert 'float' == input.type
    assert 'native' == input.form
    n1 = input.int("n1")
    assert 100 == n1
    assert 0.25 == input.float("d1")
    assert 'Time' == input.string("label1")
    n2 = 10
    output.put('n2',n2)
    output.put('label2','Distance (kft)')
    trace = np.zeros(n1,'f')
    input.read(trace)
    for i in range(n2):
        output.write(trace)
    os.system("sfrm junk.rsf")
