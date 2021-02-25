import math 
class Primitives():
    '''
        @field oper: the type of primitive, G/F/GF/FG
        @field dim_idx: the dimension our primitive is associated with (i.e which device's state)
        @field ineq_dir: the inequality direction, </>
    '''
    def __init__(self, oper, dim_idx, ineq_dir):
        self.oper = oper
        self.dim = dim_idx
        self.ineq = ineq_dir

class FLPrimitives(Primitives):
    '''
        @field param ex: F[a, b](p < c), initialized to list of nans
        @field objfunval: value for objective function when optimizing, initialized to nan
    '''
    def __init__(self, oper, dim_idx, ineq_dir, params, objfunval):
        super().__init__(oper, dim_idx, ineq_dir)
        self.param = params
        self.objfunval = objfunval
    
    def modifyparam(self, l):
        self.param = l
    
    def toString(self, dim_names = None):
        '''
            optional param: list of all devices corresponding to each dimension, 
            otherwise will just print the dimension index instead
        '''
        if dim_names:
            dim_nme = str(dim_names[self.dim])
        else:
            dim_nme = str(self.dim)
        s = "{0}: [{1}, {2}] ({3} {4} {5})".format(
            self.oper, self.param[0], self.param[1], dim_nme, self.ineq, self.param[2]
        )
        return s 

class SLPrimitives(Primitives):
    '''
        @field param ex: F[a, b]G[0, c](p < d)
        perhaps within the next "second" would mean happens immediately
        @field objfunval: value for objective function when optimizing
    '''
    def __init__(self, oper, dim_idx, ineq_dir, params, objfunval):
        super().__init__(oper, dim_idx, ineq_dir)
        self.param = params
        self.objfunval = objfunval

    def modifyparam(self, l):
        self.param = l
    
    def toString(self, dim_names = None):
        if dim_names:
            dim_nme = str(dim_names[self.dim])
        else:
            dim_nme = str(self.dim)
        if self.oper == 'GF':
            s = "G: [{0}, {1}] F: [0, {2}] ({3} {4} {5})".format(
                self.param[0], self.param[1], self.param[2], dim_nme, self.ineq, self.param[3]
            )
        else:
            s = "F: [{0}, {1}] G: [0, {2}] ({3} {4} {5})".format(
                self.param[0], self.param[1], self.param[2], dim_nme, self.ineq, self.param[3]
            )
        return s 