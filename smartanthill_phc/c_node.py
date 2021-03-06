# Copyright (C) 2015 OLogN Technologies AG
#
# This source file is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from smartanthill_phc.common import decl, expr
from smartanthill_phc.common.base import ExpressionNode, Node, StmtListNode,\
    StatementNode, TypeDeclNode, TypeNode, OnDemandResolution,\
    DeclarationListNode, Child, ChildExpr, ChildExprOpt
from smartanthill_phc.common.child import ChildList
from smartanthill_phc.common.expr import LiteralExprNode


class CastExprNode(ExpressionNode):

    '''
    Node class representing an explicit type cast
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(CastExprNode, self).__init__()
        self.cast_type = Child(self, TypeNode)
        self.expression = ChildExpr(self)


class IntegerLiteralExprNode(LiteralExprNode):

    '''
    Node class representing a number literal
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(IntegerLiteralExprNode, self).__init__()
        self.int_value = 0

    def get_static_value(self):
        '''
        Returns the float value of this literal
        Used for complile-time evaluation of expressions
        TODO check literal for validity
        '''
        return self.int_value


class BooleanLiteralExprNode(LiteralExprNode):

    '''
    Node class representing a boolean literal
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(BooleanLiteralExprNode, self).__init__()
        self.bool_value = False

    def get_static_value(self):
        '''
        Returns the bool value of this literal
        Used for complile-time evaluation of expressions
        '''
        return self.bool_value


class FunctionCallStmtNode(StatementNode):

    '''
    Node class representing a blocking function call statement
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(FunctionCallStmtNode, self).__init__()
        self.expression = ChildExpr(self)


class LoopStmtNode(StatementNode):

    '''
    Base class for loop nodes
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(LoopStmtNode, self).__init__()


class WhileStmtNode(LoopStmtNode):

    '''
    Node class representing a 'while' loop
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(WhileStmtNode, self).__init__()
        self.expression = ChildExpr(self)
        self.statement_list = Child(self, StmtListNode)


class DoWhileStmtNode(WhileStmtNode):

    '''
    Node class representing a 'do-while' loop
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(DoWhileStmtNode, self).__init__()


class ForStmtNode(LoopStmtNode):

    '''
    Node class representing a 'for' with expression and not declaration.
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(ForStmtNode, self).__init__()
        self.init_expression = ChildExprOpt(self)
        self.condition_expression = ChildExprOpt(self)
        self.iteration_expression = ChildExprOpt(self)
        self.statement_list = Child(self, StmtListNode)


class CTypeDeclNode(TypeDeclNode):

    '''
    Base class for types with added C subtypes as pointers and arrays
    '''

    def __init__(self, name):
        '''
        Constructor
        '''
        super(CTypeDeclNode, self).__init__(name)
        self.pointer = Child(self, TypeDeclNode, True)


class BasicTypeDeclNode(CTypeDeclNode):

    '''
    Basic, built-in types are implemented using this class
    '''

    def __init__(self, type_name):
        '''
        Constructor
        '''
        super(BasicTypeDeclNode, self).__init__(type_name)


class VoidTypeDeclNode(CTypeDeclNode):

    '''
    void pseudotype is implemented using this class
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(VoidTypeDeclNode, self).__init__('void')


class IntTypeDeclNode(CTypeDeclNode):

    '''
    Basic integral built-in types are implemented using this class
    '''

    def __init__(self, type_name):
        '''
        Constructor
        '''
        super(IntTypeDeclNode, self).__init__(type_name)
        self.operator_decl_list = Child(self, DeclarationListNode)
        self.cast_rules_list = Child(self, DeclarationListNode)

    def can_cast_from(self, source_type):
        '''
        Base method for type casting
        If self can be constructed from source_type returns True
        Otherwise returns False
        '''
        for each in self.cast_rules_list.get().declarations:
            if each.get().can_cast_from(source_type):
                return True
        return False

    def insert_cast_from(self, compiler, source_type, box):
        '''
        Inserts a cast from the source type
        Only implemented by types that return true to can_cast_from
        '''
        # pylint: disable=unused-argument
        for each in self.cast_rules_list.get().declarations:
            if each.get().can_cast_from(source_type):
                return each.get().insert_cast_from(compiler, source_type, box)
        assert False


class StructTypeDeclNode(CTypeDeclNode):

    '''
    Basic integral built-in types are implemented using this class
    '''

    def __init__(self, type_name):
        '''
        Constructor
        '''
        super(StructTypeDeclNode, self).__init__('struct ' + type_name)
        self.members = ChildList(self, Node)


class AttributeDeclarationNode(Node, OnDemandResolution):

    '''
    Node class representing variable declaration statement
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(AttributeDeclarationNode, self).__init__()
        self.txt_name = None
        self.declaration_type = Child(self, TypeNode)


class TrivialCastRuleNode(Node):

    '''
    Rule that integral built-in types are implemented using this class
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(TrivialCastRuleNode, self).__init__()
        self.int_min_value = 0
        self.int_max_value = 0
        self.source_type = Child(self, TypeNode)
        self.target_type = Child(self, TypeNode)

    def can_cast_from(self, source_type):
        '''
        Base method for type casting
        If self can be constructed from source_type returns True
        Otherwise returns False
        '''
        return source_type == self.source_type.get().get_type()

    def insert_cast_from(self, compiler, source_type, box):
        '''
        Inserts a cast to the target type
        '''
        assert self.can_cast_from(source_type)
        rep = expr.TrivialCastExprNode.create(
            compiler, box.get(), self.target_type.get().get_type())

        box.reset(rep)


class RefTypeNode(TypeNode):

    '''
    Node class representing hard coded type
    Used at automatic code generation
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(RefTypeNode, self).__init__()


class SimpleTypeNode(TypeNode):

    '''
    Node class representing a type
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(SimpleTypeNode, self).__init__()
        self.txt_name = None
        self.bool_const = False

    def add_qualifier(self, compiler, ctx, qualifier):
        '''
        Add qualifiers to this type.
        '''
        if qualifier == "const":
            self.bool_const = True
        else:
            super(SimpleTypeNode, self).add_qualifier(compiler, ctx, qualifier)


class InvalidTypeNode(TypeNode):

    '''
    Node class representing an error while parsing a type
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(InvalidTypeNode, self).__init__()
        self.txt_name = None


class PointerTypeNode(TypeNode):

    '''
    Node class representing an pointer to type
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(PointerTypeNode, self).__init__()
        self.pointed_type = Child(self, TypeNode)
        self.bool_const = False

    def add_qualifier(self, compiler, ctx, qualifier):
        '''
        Add qualifiers to this type.
        '''
        # pylint: disable=no-self-use
        if qualifier == "const":
            self.bool_const = True
        else:
            super(PointerTypeNode, self).add_qualifier(
                compiler, ctx, qualifier)


class PapiFunctionDeclNode(decl.FunctionDeclNode):

    '''
    Node class representing a plugin api function
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(PapiFunctionDeclNode, self).__init__()


class TypedefStmtNode(StatementNode, OnDemandResolution):

    '''
    Node class representing variable declaration statement
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(TypedefStmtNode, self).__init__()
        self.txt_name = None
        self.typedef_type = Child(self, TypeNode)

    def add_qualifier(self, compiler, ctx, qualifier):
        '''
        Add qualifiers to this type.
        '''
        # pylint: disable=no-self-use
        if qualifier == "typedef":
            pass
        else:
            super(TypedefStmtNode, self).add_qualifier(
                compiler, ctx, qualifier)


class PreprocessorDirectiveNode(Node):

    '''
    Node class representing a preprocessor directive
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(PreprocessorDirectiveNode, self).__init__()
        self.txt_body = None


class IncludeFileNode(Node):

    '''
    Node class representing an #include preprocessor directive
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(IncludeFileNode, self).__init__()
        self.txt_file_name = None


class ConstantDefineNode(Node, OnDemandResolution):

    '''
    Node class representing a preprocessor directive
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(ConstantDefineNode, self).__init__()
        self.txt_name = None
        self.expression = ChildExpr(self)

    def get_static_value(self):
        '''
        Returns compile-time value of this declaration
        '''

        return self.expression.get().get_static_value()


class OperatorDeclNode(decl.FunctionDeclNode):

    '''
    Node class representing a function declaration
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(OperatorDeclNode, self).__init__()


class StaticAssertStmtNode(Node):

    '''
    Node class representing a preprocessor directive
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(StaticAssertStmtNode, self).__init__()
        self.expression = ChildExpr(self)
        self.txt_description = None
