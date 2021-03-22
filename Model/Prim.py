import math 

def negateIneq(ineq):
    if ineq == '<':
        return '>='
    if ineq == '>':
        return '<='
    if ineq == '<=':
        return '>'
    return '<'

class Primitives():
    '''
        @field oper: the type of primitive, G/F/GF/FG
        @field dim_idx: the dimension our primitive is associated with (i.e which device's state)
        @field ineq_dir: the inequality direction, </>
    '''
    def __init__(self, oper, dim_idx, dimname, ineq_dir):
        self.oper = oper
        self.dim = dim_idx
        self.dimname = dimname
        self.ineq = ineq_dir

class FLPrimitives(Primitives):
    '''
        @field param ex: F[a, b](p < c), initialized to list of nans
        @field objfunval: value for objective function when optimizing, initialized to nan
    '''
    def __init__(self, oper, dim_idx, dimname, ineq_dir, params, objfunval):
        super().__init__(oper, dim_idx, dimname, ineq_dir)
        self.param = params
        self.objfunval = objfunval
    
    def modifyparam(self, l):
        self.param = l
    
    def convertIneq(self):
        if self.oper == 'F':
            if self.ineq == '<':
                return '<='
            else:
                return '>='
        return self.ineq 

    def toString(self):
        '''
            optional param: list of all devices corresponding to each dimension, 
            otherwise will just print the dimension index instead
        '''
        s = "{0}: [{1}, {2}] ({3} {4} {5})".format(
            self.oper, self.param[0], self.param[1], 
            self.dimname, self.convertIneq(), self.param[2]
        )
        return s + "\n\t Translate:" + self.toWordString()
    
    def toWordString(self):
        translate = ''
        if self.oper == 'F':
            translate = 'Between seconds {0} to {1}, {2} becomes {3} {4}'.format(
                self.param[0], self.param[1], self.dimname, self.convertIneq(), self.param[2]
            )
        else:
            translate = 'From seconds {0} to {1}, {2} is always {3} {4}'.format(
                self.param[0], self.param[1], self.dimname, self.convertIneq(), self.param[2]
            )
        return translate
    
    def negateWordString(self, dim_names = None):
        negate = ''
        if self.oper == 'F':
            negate = 'From seconds {0} to {1}, {2} is always {3} {4}'.format(
                self.param[0], self.param[1], self.dimname, negateIneq(self.convertIneq()), self.param[2]
            )
        else:
            negate = 'Between seconds {0} to {1}, {2} becomes {3} {4}'.format(
                self.param[0], self.param[1], self.dimname, negateIneq(self.convertIneq()), self.param[2]
            )
        return negate 

class SLPrimitives(Primitives):
    '''
        @field param ex: F[a, b]G[0, c](p < d)
        perhaps within the next "second" would mean happens immediately
        @field objfunval: value for objective function when optimizing
    '''
    def __init__(self, oper, dim_idx, dimname, ineq_dir, params, objfunval):
        super().__init__(oper, dim_idx, dimname, ineq_dir)
        self.param = params
        self.objfunval = objfunval

    def modifyparam(self, l):
        self.param = l
    
    def convertIneq(self):
        if self.oper == 'GF':
            if self.ineq == '<':
                return '<='
            else:
                return '>='
        return self.ineq

    def toString(self):
        if self.oper == 'GF':
            s = "G: [{0}, {1}] F: [0, {2}] ({3} {4} {5})".format(
                self.param[0], self.param[1], self.param[2], self.dimname, self.convertIneq(), self.param[3]
            )
        else:
            s = "F: [{0}, {1}] G: [0, {2}] ({3} {4} {5})".format(
                self.param[0], self.param[1], self.param[2], self.dimname, self.convertIneq(), self.param[3]
            )
        return s + "\n\t Translate" + self.toWordString()

    def toWordString(self):
        translate = ''
        if self.oper == 'GF':
            translate = 'In anytime from {0} to {1}, {3} becomes {4} {5} within {2} seconds'.format(
                self.param[0], self.param[1], self.param[2], self.dimname, self.convertIneq(), self.param[3]
            )
        else:
            translate = 'From {0} to {1}, {3} becomes {4} {5} for at least {2} seconds'.format(
                self.param[0], self.param[1], self.param[2], self.dimname, self.convertIneq(), self.param[3]
            )
        return translate
    
    def negateWordString(self, dim_names = None):
        negate = ''
        if self.oper == 'GF':
            negate = 'From {0} to {1}, {3} becomes {4} {5} for at least {2} seconds'.format(
                self.param[0], self.param[1], self.param[2], self.dimname, negateIneq(self.convertIneq()), self.param[3]
            )
        else:
            negate = 'In anytime from {0} to {1}, {3} becomes {4} {5} within {2} seconds'.format(
                self.param[0], self.param[1], self.param[2], self.dimname, negateIneq(self.convertIneq()), self.param[3]
            )
        return negate 