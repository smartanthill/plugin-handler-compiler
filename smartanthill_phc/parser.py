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


from smartanthill_phc import c_node, root
from smartanthill_phc.antlr_parser import CVisitor, CParser
from smartanthill_phc.common import base, decl, expr, stmt
from smartanthill_phc.common.antlr_helper import get_identifier_text

_prefix = 'sa_'


def c_parse_tree_to_syntax_tree(compiler, tree, prefix):
    '''
    Translates a parse tree as returned by antlr4 into a
    syntax tree as used by the compiler, this tree transformation
    replaces syntax directed translation written directly into the grammar
    as used by yacc-lex.
    The antlr parser creates a parse tree from the grammar without actions,
    and at this point the parse tree is transformed into the syntax tree
    needed by the application.
    '''

    assert isinstance(tree, CParser.CParser.CompilationUnitContext)

    source = compiler.init_node(root.PluginSourceNode(), tree)
    source.txt_prefix = prefix
    ls = compiler.init_node(base.DeclarationListNode(), tree)
    source.declaration_list.set(ls)
    v = _CParseTreeVisitor(compiler, source)
    v.visit(tree)

    compiler.check_stage('syntax')

    return source


_blocking_funcs = [
    "papi_sleep",
    "papi_wait_for_spi_send",
    "papi_wait_for_i2c_send",
    "papi_wait_for_spi_receive",
    "papi_wait_for_i2c_receive"
]


def _is_blocking_api_function(name):
    '''
    Returns true if this name is in blocking api functions list
    '''
    return name in _blocking_funcs


def _get_direct_declarator_id(ctx):

    assert isinstance(ctx, CParser.CParser.DirectDeclaratorContext)
    if ctx.Identifier() is not None:
        return ctx.Identifier()
#     elif ctx.declarator() is not None:
#         return get_declarator_name(ctx.declarator())
    else:
        assert ctx.directDeclarator() is not None
        return _get_direct_declarator_id(ctx.directDeclarator())


def get_declarator_identifier(ctx):
    '''
    Returns the Identifier token from a nested declarator
    '''
    assert isinstance(ctx, CParser.CParser.DeclaratorContext)
    return _get_direct_declarator_id(ctx.directDeclarator())


def process_pointers(compiler, ctx, t):

    last = t
    current = ctx
    while current is not None:

        ptr = compiler.init_node(c_node.PointerTypeNode(), ctx)
        ptr.pointed_type.set(last)

        for each in ctx.typeQualifier():
            ptr.add_qualifier(compiler, each, get_text(each))

        current = current.pointer()
        last = ptr

    return last


def process_type_specifiers_and_qualifiers(compiler, ts, tq):

    assert len(ts) != 0
    if len(ts) != 1:
        for each in ts:
            if each.atomicTypeSpecifier() is not None or\
                    each.structOrUnionSpecifier() is not None or\
                    each.enumSpecifier() is not None or\
                    each.typedefName() is not None:
                compiler.report_error(each,
                                      "Invalid type specifier combination")

    if ts[0].structOrUnionSpecifier() is not None:
        compiler.report_error(ts[0], "Unsupported type")
        t = compiler.init_node(c_node.InvalidTypeNode(), ts[0])
    elif ts[0].enumSpecifier() is not None:
        compiler.report_error(ts[0], "Unsupported type")
        t = compiler.init_node(c_node.InvalidTypeNode(), ts[0])
    elif ts[0].typedefName() is not None:
        t = compiler.init_node(c_node.SimpleTypeNode(), ts[0])
        t.txt_name = get_text(ts[0])
    else:
        t = compiler.init_node(c_node.SimpleTypeNode(), ts[0])
        t.txt_name = ' '.join([get_text(each) for each in ts])

    for each in tq:
        t.add_qualifier(compiler, each, get_text(each))

    return t


def process_specifiers(compiler, ctxs):

    stor = None
    others = []
    ts = []
    tq = []
    for each in ctxs:
        if each.storageClassSpecifier() is not None:
            if stor is None:
                stor = each.storageClassSpecifier()
            else:
                compiler.report_error(
                    each, "More than one storage specifier not allowed")
        elif each.functionSpecifier() is not None:
            others.append(each.functionSpecifier())
        elif each.typeSpecifier() is not None:
            ts.append(each.typeSpecifier())
        elif each.typeQualifier() is not None:
            tq.append(each.typeQualifier())
        else:
            assert False

    return stor, others, ts, tq


def process_qualifiers(compiler, node, stor, others):
    '''
    Adds qualifiers to node
    '''
    if stor is not None:
        node.add_qualifier(compiler, stor, get_text(stor))
    for each in others:
        node.add_qualifier(compiler, each, get_text(each))


def get_text(ctx):
    return str(ctx.getText())

# Generated from java-escape by ANTLR 4.5
# This class defines a complete generic visitor for a parse tree produced
# by CParser.


class _CParseTreeVisitor(CVisitor.CVisitor):

    '''
    The template for the visitor is copy&paste from super class interface
    ECMAScriptVisitor.ECMAScriptVisitor
    '''

    def __init__(self, compiler, source):
        '''
        Constructor
        '''
        self._c = compiler
        self._s = source

    def _get_stmt_list(self, ctx):
        '''
        Visits and returns an statement list
        If child is a single statement without curly braces,
        error is reported
        '''
        statement = self.visit(ctx)

        if not isinstance(statement, base.StmtListNode):
            self._c.report_error(
                ctx, "Single statement without curly braces {} not allowed")

        # make an stmt list out of it, to avoid assert errors on setters
        return stmt.make_statement_list(self._c, statement)

    def visitChildren(self, current):
        '''
        Overrides antlr4.ParseTreeVisitor method
        Changes default action, from walking down the tree to
        fail with assert, this will expose any parsed base that does not have
        a valid interpretation rule here
        '''
        print "Context: %s" % type(current).__name__
        self._c.report_error(current, "Unsupported syntax!")
        self._c.raise_error()

    # Visit a parse tree produced by CParser#FunctionExpression.
    def visitFunctionExpression(self, ctx):

        if not isinstance(ctx.unaryExpression(),
                          CParser.CParser.IdentifierExpressionContext):
            self._c.report_error(ctx, "Unsupported function call syntax")

        node = self._c.init_node(expr.FunctionCallExprNode(), ctx)
        node.txt_name = get_identifier_text(
            self._c, ctx.unaryExpression().Identifier(), _prefix)
        node.bool_is_blocking = _is_blocking_api_function(node.txt_name)

        if ctx.argumentExpressionList() is not None:
            args = self._make_args(
                ctx.getChild(1),
                ctx.argumentExpressionList().assignmentExpression())
        else:
            args = self._c.init_node(base.ArgumentListNode(), ctx.getChild(1))

        node.argument_list.set(args)

        return node

    # Visit a parse tree produced by CParser#DotExpression.
    def visitDotExpression(self, ctx):

        node = self._c.init_node(expr.MemberAccessExprNode(), ctx)
        node.bool_arrow = False

        node.expression.set(self.visit(ctx.unaryExpression()))

        tk = ctx.Identifier()
        node.txt_name = get_identifier_text(self._c, tk, _prefix)

        return node

    # Visit a parse tree produced by CParser#ParenthesizedExpression.
    def visitParenthesizedExpression(self, ctx):

        node = self.visit(ctx.expression())
        node.bool_parenthesis = True

        return node

    # Visit a parse tree produced by CParser#LiteralExpression.
    def visitFloatingLiteralExpression(self, ctx):

        self._c.report_error(ctx, "Floating literals not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)
        return node

    # Visit a parse tree produced by CParser#PostIncrementExpression.
    def visitPostIncrementExpression(self, ctx):

        node = self._c.init_node(expr.PostUnaryOpExprNode(), ctx)
        node.txt_operator = 'post' + get_text(ctx.getChild(1))
        node.expression.set(self.visit(ctx.unaryExpression()))
        node.argument_list.set(self._make_args(ctx, []))

        return node

    # Visit a parse tree produced by CParser#CharacterLiteralExpression.
    def visitCharacterLiteralExpression(self, ctx):

        self._c.report_error(ctx, "Character literals not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)
        return node

    # Visit a parse tree produced by CParser#ArrowExpression.
    def visitArrowExpression(self, ctx):

        node = self._c.init_node(expr.MemberAccessExprNode(), ctx)
        node.bool_arrow = True

        node.expression.set(self.visit(ctx.unaryExpression()))

        tk = ctx.Identifier()
        node.txt_name = get_identifier_text(self._c, tk, _prefix)

        return node

    # Visit a parse tree produced by CParser#IndexExpression.
    def visitIndexExpression(self, ctx):

        node = self._c.init_node(expr.IndexOpExprNode(), ctx)
        node.txt_operator = '[]'
        node.expression.set(self.visit(ctx.unaryExpression()))

        args = self._make_args(ctx, [ctx.expression()])
        node.argument_list.set(args)

        return node

    # Visit a parse tree produced by CParser#SizeOfTypeExpression.
    def visitSizeOfTypeExpression(self, ctx):

        self._c.report_error(ctx, "sizeof not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)

        return node

    # Visit a parse tree produced by CParser#IdentifierExpression.
    def visitIdentifierExpression(self, ctx):

        tk = ctx.Identifier()
        node = self._c.init_node(expr.VariableExprNode(), tk)
        node.txt_name = get_identifier_text(self._c, tk, _prefix)

        return node

    # Visit a parse tree produced by CParser#UnaryOperatorExpression.
    def visitUnaryOperatorExpression(self, ctx):

        op = get_text(ctx.getChild(0))
        if op == '*':
            node = self._c.init_node(expr.PointerExprNode(), ctx)
            node.expression.set(self.visit(ctx.castExpression()))
        elif op == '&':
            node = self._c.init_node(expr.AddressOfExprNode(), ctx)
            node.expression.set(self.visit(ctx.castExpression()))
        elif op in ['+', '-', '~', '!']:
            node = self._c.init_node(expr.UnaryOpExprNode(), ctx)
            node.txt_operator = get_text(ctx.getChild(0))
            node.expression.set(self.visit(ctx.castExpression()))
            node.argument_list.set(self._make_args(ctx, []))
        else:
            assert False

        return node

    # Visit a parse tree produced by CParser#AlignOfTypeExpression.
    def visitAlignOfTypeExpression(self, ctx):
        self._c.report_error(ctx, "_Alignof not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)
        return node

    # Visit a parse tree produced by CParser#SizeOfExpression.
    def visitSizeOfExpression(self, ctx):
        self._c.report_error(ctx, "sizeof not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)
        return node

    # Visit a parse tree produced by CParser#IntegerLiteralExpression.
    def visitIntegerLiteralExpression(self, ctx):
        node = self._c.init_node(c_node.IntegerLiteralExprNode(), ctx)
        node.txt_literal = get_text(ctx.IntegerConstant())

        return node

    # Visit a parse tree produced by CParser#StringLiteralExpression.
    def visitStringLiteralExpression(self, ctx):
        self._c.report_error(ctx, "string literal not supported")
        node = self._c.init_node(expr.ErrorExprNode(), ctx)
        return node

    # Visit a parse tree produced by CParser#PreIncrementExpression.
    def visitPreIncrementExpression(self, ctx):

        node = self._c.init_node(expr.UnaryOpExprNode(), ctx)
        node.txt_operator = get_text(ctx.getChild(0))
        node.expression.set(self.visit(ctx.unaryExpression()))
        node.argument_list.set(self._make_args(ctx, []))

        return node

    # Visit a parse tree produced by CParser#argumentExpressionList.
    def visitArgumentExpressionList(self, ctx):

        args = self._c.init_node(base.ArgumentListNode(), ctx)

        for e in ctx.assignmentExpression():
            node = self.visit(e)
            args.arguments.add(node)

        return args

    # Visit a parse tree produced by CParser#castExpression.
    def visitCastExpression(self, ctx):

        if ctx.unaryExpression() is not None:
            return self.visit(ctx.unaryExpression())
        else:
            node = self._c.init_node(c_node.CastExprNode(), ctx)
            node.cast_type.set(self.visit(ctx.typeName()))
            node.expression.set(self.visit(ctx.castExpression()))

            return node

    def _make_args(self, ctx, expressions):

        args = self._c.init_node(base.ArgumentListNode(), ctx)
        for each in expressions:
            args.arguments.add(self.visit(each))

        return args

    # Visit a parse tree produced by CParser#logicalOrExpression.
    def visitLogicalOrExpression(self, ctx):

        if ctx.castExpression() is not None:
            return self.visit(ctx.castExpression())
        else:
            op = get_text(ctx.getChild(1))
            if op not in ('&&', '||', '*', '/', '%', '+', '-', '<', '>',
                          '<=', '>=', '==', '!='):
                self._c.report_error(ctx, "Operator '%s' not supported" % op)

            node = self._c.init_node(expr.BinaryOpExprNode(), ctx)

            node.txt_operator = op
            args = self._make_args(ctx, ctx.logicalOrExpression())
            node.argument_list.set(args)

            return node

    # Visit a parse tree produced by CParser#conditionalExpression.
    def visitConditionalExpression(self, ctx):
        if ctx.expression() is None:
            assert ctx.conditionalExpression() is None

            return self.visit(ctx.logicalOrExpression())
        else:
            node = self._c.init_node(expr.ConditionalExprNode(), ctx)
            node.condition_expression.set(
                self.visit(ctx.logicalOrExpression()))
            node.true_expression.set(self.visit(ctx.expression()))
            node.false_expression.set(self.visit(ctx.conditionalExpression()))

            return node

    # Visit a parse tree produced by CParser#assignmentExpression.
    def visitAssignmentExpression(self, ctx):
        if ctx.conditionalExpression() is not None:
            return self.visit(ctx.conditionalExpression())
        else:
            op = get_text(ctx.getChild(1))
            if op == '=':

                node = self._c.init_node(expr.AssignmentExprNode(), ctx)

                node.left_expression.set(self.visit(ctx.unaryExpression()))
                node.right_expression.set(
                    self.visit(ctx.assignmentExpression()))
            elif op in ('*=', '/=', '%=', '+=', '-=', '<<=', '>>=',
                        '&=', '^=', '|='):

                node = self._c.init_node(expr.MemberBinaryOpExprNode(), ctx)
                node.txt_operator = op
                node.expression.set(self.visit(ctx.unaryExpression()))
                args = self._make_args(ctx, [ctx.assignmentExpression()])
                node.argument_list.set(args)
                return node
            else:
                assert False

            return node

    # Visit a parse tree produced by CParser#expr.
    def visitExpression(self, ctx):
        if len(ctx.assignmentExpression()) > 1:
            self._c.report_errot(ctx, "Comma expression not supported")

        return self.visit(ctx.assignmentExpression(0))

    # Visit a parse tree produced by CParser#constantExpression.
    def visitConstantExpression(self, ctx):
        return self.visit(ctx.conditionalExpression())

    # Visit a parse tree produced by CParser#declaration.
    def visitDeclaration(self, ctx):

        stor, others, ts, tq = process_specifiers(
            self._c, ctx.declarationSpecifier())

        is_typedef = stor is not None and get_text(stor) == "typedef"

        # typedef may hit two different rule sets
        if is_typedef and ctx.initDeclaratorList() is None:

            if len(ts) < 2 or ts[-1].typedefName() is None:
                self._c.report_error(ctx, "Invalid typedef declaration")
                return []

            node = self._c.init_node(c_node.TypedefStmtNode(), ctx)

            n = ts.pop(-1)
            node.txt_name = get_identifier_text(
                self._c, n.typedefName().Identifier(), _prefix)

            t = process_type_specifiers_and_qualifiers(self._c, ts, tq)
            node.typedef_type.set(t)

        else:

            if ctx.initDeclaratorList() is None:
                # TODO this is a type declaration without name
                self._c.report_error(
                    ctx, "Incomplete declaration not supported")
                return []

            if len(ctx.initDeclaratorList().initDeclarator()) != 1:
                self._c.report_error(ctx, "Combined declaration not supported")
                return []

            init_decl = ctx.initDeclaratorList().initDeclarator()[0]
            dd = init_decl.declarator().directDeclarator()

            t = process_type_specifiers_and_qualifiers(self._c, ts, tq)
            t = process_pointers(self._c, init_decl.declarator().pointer(), t)

            if is_typedef:
                node = self._c.init_node(c_node.TypedefStmtNode(), ctx)
                node.txt_name = get_identifier_text(
                    self._c, dd.Identifier(), _prefix)

                node.typedef_type.set(t)

            elif dd.Identifier() is not None:
                # variable decl
                node = self._c.init_node(
                    stmt.VariableDeclarationStmtNode(), ctx)
                node.txt_name = get_identifier_text(
                    self._c, dd.Identifier(), _prefix)

                node.declaration_type.set(t)

                if init_decl.initializer() is not None:
                    e = self.visit(init_decl.initializer())
                    node.initializer_expression.set(e)

            elif dd.directDeclarator() is not None:
                # function decl
                if dd.directDeclarator().Identifier() is None:
                    self._c.report_error(ctx, "Invalid function declaration")
                    return []

                node = self._c.init_node(
                    decl.FunctionDeclNode(), init_decl.declarator())

                node.txt_name = get_identifier_text(
                    self._c, dd.directDeclarator().Identifier(), _prefix)

                node.return_type.set(t)

                al = self._c.init_node(
                    decl.ArgumentDeclListNode(), dd.getChild(1))
                # add argument declarations
                self._process_arg_list(dd.parameterTypeList(), al)
                node.argument_decl_list.set(al)
            else:
                self._c.report_error(ctx, "Unsupported declaration")
                return []

        process_qualifiers(self._c, node, stor, others)
        return [node]

    # Visit a parse tree produced by CParser#declarationSpecifier.
    def visitDeclarationSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#initDeclaratorList.
    def visitInitDeclaratorList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#initDeclarator.
    def visitInitDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#storageClassSpecifier.
    def visitStorageClassSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#structOrUnionSpecifier.
    def visitStructOrUnionSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#structOrUnion.
    def visitStructOrUnion(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#structDeclaration.
    def visitStructDeclaration(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#specifierQualifierList.
    def visitSpecifierQualifierList(self, ctx):

        ts = []
        tq = []
        current = ctx
        while current is not None:
            if current.typeSpecifier() is not None:
                ts.append(current.typeSpecifier())
            elif current.typeQualifier() is not None:
                tq.append(current.typeQualifier())
            else:
                assert False

            current = current.specifierQualifierList()

        t = process_type_specifiers_and_qualifiers(self._c, ts, tq)
        return t

    # Visit a parse tree produced by CParser#structDeclaratorList.
    def visitStructDeclaratorList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#structDeclarator.
    def visitStructDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#enumSpecifier.
    def visitEnumSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#enumeratorList.
    def visitEnumeratorList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#enumerator.
    def visitEnumerator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#atomicTypeSpecifier.
    def visitAtomicTypeSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#functionSpecifier.
    def visitFunctionSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#alignmentSpecifier.
    def visitAlignmentSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#declarator.
    def visitDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#directDeclarator.
    def visitDirectDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#gccDeclaratorExtension.
    def visitGccDeclaratorExtension(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#gccAttributeSpecifier.
    def visitGccAttributeSpecifier(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#gccAttributeList.
    def visitGccAttributeList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#gccAttribute.
    def visitGccAttribute(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#nestedParenthesesBlock.
    def visitNestedParenthesesBlock(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#parameterTypeList.
    def visitParameterTypeList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#parameterDeclaration.
    def visitParameterDeclaration(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#identifierList.
    def visitIdentifierList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#typeName.
    def visitTypeName(self, ctx):

        t = self.visit(ctx.specifierQualifierList())
        ad = ctx.abstractDeclarator()
        if ad is not None:
            if ad.directAbstractDeclarator() is not None:
                self._c.report_error(ctx, "Unsupported type")
            else:
                t = process_pointers(self._c, ad.pointer(), t)

        return t

    # Visit a parse tree produced by CParser#abstractDeclarator.
    def visitAbstractDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#directAbstractDeclarator.
    def visitDirectAbstractDeclarator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#typedefName.
    def visitTypedefName(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#initializer.
    def visitInitializer(self, ctx):

        if ctx.assignmentExpression() is not None:
            return self.visit(ctx.assignmentExpression())
        else:
            return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#initializerList.
    def visitInitializerList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#designation.
    def visitDesignation(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#designatorList.
    def visitDesignatorList(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#designator.
    def visitDesignator(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#staticAssertDeclaration.
    def visitStaticAssertDeclaration(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#stmt.
    def visitStatement(self, ctx):
        return self.visit(ctx.getChild(0))

    # Visit a parse tree produced by CParser#labeledStatement.
    def visitLabeledStatement(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#compoundStatement.
    def visitCompoundStatement(self, ctx):

        sl = self._c.init_node(base.StmtListNode(), ctx)
        for each in ctx.blockItem():
            s = self.visit(each)
            if isinstance(s, base.StatementNode):
                sl.statements.add(s)
            else:
                sl.statements.add_all(s)

        return sl

    # Visit a parse tree produced by CParser#blockItem.
    def visitBlockItem(self, ctx):
        return self.visit(ctx.getChild(0))

    # Visit a parse tree produced by CParser#expressionStatement.
    def visitExpressionStatement(self, ctx):

        if ctx.expression():
            e = self.visit(ctx.expression())
            if isinstance(e, expr.FunctionCallExprNode):

                s = self._c.init_node(c_node.FunctionCallStmtNode(), ctx)
                s.expression.set(e)

                return s
            else:
                s = self._c.init_node(stmt.ExpressionStmtNode(), ctx)
                s.expression.set(e)
                return s
        else:
            return self._c.init_node(stmt.NopStmtNode(), ctx)

    # Visit a parse tree produced by CParser#IfStatement.
    def visitIfStatement(self, ctx):
        s = self._c.init_node(stmt.IfElseStmtNode(), ctx)
        e = self.visit(ctx.expression())
        s.expression.set(e)

        assert len(ctx.statement()) >= 1
        if_stmt = self.visit(ctx.statement()[0])

        if not isinstance(if_stmt, base.StmtListNode):
            self._c.report_error(
                ctx.statement()[0],
                "Single stmt without curly braces {} not allowed")

        if_stmt = stmt.make_statement_list(self._c, if_stmt)
        s.if_stmt_list.set(if_stmt)

        if len(ctx.statement()) >= 2:
            else_stmt = self.visit(ctx.statement()[1])
            if not isinstance(else_stmt, base.StmtListNode):
                self._c.report_error(
                    ctx.statement()[1],
                    "Single stmt without curly braces {} not allowed")

            else_stmt = stmt.make_statement_list(self._c, else_stmt)
            s.else_stmt_list.set(else_stmt)

        return s

    # Visit a parse tree produced by CParser#SwitchStatement.
    def visitSwitchStatement(self, ctx):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CParser#WhileStatement.
    def visitWhileStatement(self, ctx):
        s = self._c.init_node(c_node.WhileStmtNode(), ctx)

        e = self.visit(ctx.expression())
        s.expression.set(e)

        stmt_list = self._get_stmt_list(ctx.statement())
        s.statement_list.set(stmt_list)

        return s

    # Visit a parse tree produced by CParser#DoWhileStatement.
    def visitDoWhileStatement(self, ctx):
        s = self._c.init_node(c_node.DoWhileStmtNode(), ctx)

        e = self.visit(ctx.expression())
        s.expression.set(e)

        stmt_list = self._get_stmt_list(ctx.statement())
        s.statement_list.set(stmt_list)

        return s

    # Visit a parse tree produced by CParser#ForStatement.
    def visitForStatement(self, ctx):

        loop = self._c.init_node(c_node.ForStmtNode(), ctx)

        if ctx.initExpression() is not None:
            loop.init_expression.set(
                self.visit(ctx.initExpression().expression()))

        if ctx.expression() is not None:
            loop.condition_expression.set(self.visit(ctx.expression()))

        if ctx.iterationExpression() is not None:
            loop.iteration_expression.set(
                self.visit(ctx.iterationExpression().expression()))

        body = self._get_stmt_list(ctx.statement())
        loop.statement_list.set(body)

        return loop

    # Visit a parse tree produced by CParser#DeclForStatement.
    def visitDeclForStatement(self, ctx):

        sl = self._c.init_node(base.StmtListNode(), ctx)
        for each in self.visit(ctx.declaration()):
            sl.statements.add(each)

        loop = self._c.init_node(c_node.ForStmtNode(), ctx)

        if ctx.expression() is not None:
            loop.condition_expression.set(self.visit(ctx.expression()))

        if ctx.iterationExpression() is not None:
            loop.iteration_expression.set(
                self.visit(ctx.iterationExpression().expression()))

        body = self._get_stmt_list(ctx.statement())
        loop.statement_list.set(body)

        sl.statements.add(loop)

        return sl

    # Visit a parse tree produced by CParser#ReturnStatement.
    def visitReturnStatement(self, ctx):

        s = self._c.init_node(stmt.ReturnStmtNode(), ctx)
        if ctx.expression() is not None:
            e = self.visit(ctx.expression())
            s.expression.set(e)

        return s

    # Visit a parse tree produced by CParser#compilationUnit.
    def visitCompilationUnit(self, ctx):

        for d in ctx.externalDeclaration():
            self.visit(d)

        return None

    # Visit a parse tree produced by CParser#externalDeclaration.
    def visitExternalDeclaration(self, ctx):

        if ctx.functionDefinition() is not None:
            self.visit(ctx.functionDefinition())
        elif ctx.declaration() is not None:
            decls = self.visit(ctx.declaration())
            for each in decls:
                self._s.declaration_list.get().declarations.add(each)
        elif ctx.preprocessorDirective() is not None:
            self.visit(ctx.preprocessorDirective())

    def _process_arg_list(self, parameterTypeList, al):
        if parameterTypeList is not None:

            for each in parameterTypeList.parameterDeclaration():

                arg = self._c.init_node(decl.ArgumentDeclNode(), each)
                al.declarations.add(arg)
                stor, others, ts, tq = process_specifiers(
                    self._c, each.declarationSpecifier())

                process_qualifiers(self._c, arg, stor, others)
                t = process_type_specifiers_and_qualifiers(self._c, ts, tq)

                if each.declarator() is not None:

                    t = process_pointers(
                        self._c, each.declarator().pointer(), t)

                    i = each.declarator().directDeclarator().Identifier()
                    if i is None:
                        self._c.report_error(each, "Unsupported parameter")

                    arg.txt_name = get_identifier_text(self._c, i, _prefix)

                elif each.abstractDeclarator() is not None:
                    t = process_pointers(
                        self._c, each.abstractDeclarator().pointer(), t)

                    if each.abstractDeclarator()\
                            .directAbstractDeclarator() is not None:
                        self._c.report_error(each,
                                             "Unsupported parameter")

                arg.argument_type.set(t)

    # Visit a parse tree produced by CParser#functionDefinition.
    def visitFunctionDefinition(self, ctx):

        if len(ctx.declarationSpecifier()) == 0:
            self._c.report_error(ctx, "Unsupported implicit return type")
            return

        dd = ctx.declarator().directDeclarator()
        if dd.Identifier() is not None:
            self._c.report_error(ctx, "Invalid function declaration")
            return

        assert dd.directDeclarator() is not None
        if dd.directDeclarator().Identifier() is None:
            self._c.report_error(ctx, "Invalid function declaration")
            return

        definition = self._c.init_node(decl.FunctionDefinitionNode(), ctx)
        declaration = self._c.init_node(
            decl.FunctionDeclNode(), ctx.declarator())

        declaration.txt_name = get_identifier_text(
            self._c, dd.directDeclarator().Identifier(), _prefix)

        stor, others, ts, tq = process_specifiers(
            self._c, ctx.declarationSpecifier())

        process_qualifiers(self._c, declaration, stor, others)
        t = process_type_specifiers_and_qualifiers(self._c, ts, tq)
        t = process_pointers(self._c, ctx.declarator().pointer(), t)

        declaration.return_type.set(t)

        al = self._c.init_node(decl.ArgumentDeclListNode(), dd.getChild(1))
        # add argument declarations
        self._process_arg_list(dd.parameterTypeList(), al)
        declaration.argument_decl_list.set(al)

        definition.declaration.set(declaration)
        sl = self.visit(ctx.compoundStatement())
        definition.statement_list.set(sl)

        self._s.declaration_list.get().declarations.add(definition)

        return None

    # Visit a parse tree produced by CParser#preprocessorDirective.
    def visitPreprocessorDirective(self, ctx):

        if ctx.includeDirective() is not None:
            node = self._c.init_node(c_node.IncludeFileNode(), ctx)
            node.txt_file_name = get_text(
                ctx.includeDirective().StringLiteral())
        elif ctx.defineConstantDirective() is not None:
            node = self._c.init_node(c_node.ConstantDefineNode(), ctx)
            node.txt_name = get_identifier_text(
                self._c, ctx.defineConstantDirective().Identifier(), _prefix)
            node.expression.set(
                self.visit(ctx.defineConstantDirective().expression()))
#         elif ctx.defineFunctionDirective() is not None:
#             pass
        else:
            node = self._c.init_node(c_node.PreprocessorDirectiveNode(), ctx)
            node.txt_body = get_text(ctx)

        self._s.declaration_list.get().declarations.add(node)
