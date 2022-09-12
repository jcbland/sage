r"""
Combinatorial diagrams

A combinatorial diagram is a collection of cells `(i,j)` indexed by pairs of
natural numbers.

For arbitrary diagrams, see :class:`Diagram`. There are also two other specific
types of diagrams implemented here. They are northwest diagrams
(:class:`NorthwestDiagram`) and Rothe diagrams (:func:`RotheDiagram`, a special
kind of northwest diagram).

AUTHORS:

- Trevor K. Karn (2022-08-01): initial version
"""

# ****************************************************************************
#       Copyright (C) 2022 Trevor K. Karn <karnx018 (at) umn.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************

from sage.categories.sets_cat import Sets
from sage.sets.non_negative_integers import NonNegativeIntegers as NN
from sage.combinat.partition import Partition
from sage.combinat.skew_partition import SkewPartition
from sage.combinat.permutation import Permutations
from sage.structure.unique_representation import UniqueRepresentation
from sage.structure.list_clone import ClonableArray
from sage.structure.parent import Parent
from sage.combinat.tableau import Tableau
from sage.combinat.skew_tableau import SkewTableaux
from sage.misc.inherit_comparison import InheritComparisonClasscallMetaclass


class Diagram(ClonableArray, metaclass=InheritComparisonClasscallMetaclass):
    r"""
    Combinatorial diagrams with positions indexed by rows in columns.

    The positions are indexed by rows and columns as in a matrix. For example,
    a Ferrer's diagram is a diagram obtained from a partition
    `\lambda = (\lambda_0, \lambda_1, \ldots, \lambda_\ell)` where the cells are
    in rows `i` for `0 \leq i \leq \ell` and the cells in row `i` consist of
    `(i,j)` for `0 \leq j < \lambda_i`. In English notation, the indices are
    read from top left to bottom right as in a matrix.

    Indexing conventions are the same as
    :class:`~sage.combinat.partition.Partition`. Printing the diagram of a
    partition, however, will always be in English notation.

    EXAMPLES:

    To create an arbirtrary diagram, pass a list of all cells::

        sage: from sage.combinat.diagram import Diagram
        sage: cells = [(0,0), (0,1), (1,0), (1,1), (4,4), (4,5), (4,6), (5,4), (7, 6)]
        sage: D = Diagram(cells); D
        [(0, 0), (0, 1), (1, 0), (1, 1), (4, 4), (4, 5), (4, 6), (5, 4), (7, 6)]

    We can visualize the diagram by printing ``O``'s and ``.``'s. ``O``'s are
    present in the cells which are present in the diagram and a ``.`` represents
    the absence of a cell in the diagram::

        sage: D.pp()
        O O . . . . .
        O O . . . . .
        . . . . . . .
        . . . . . . .
        . . . . O O O
        . . . . O . .
        . . . . . . .
        . . . . . . O

    We can also check if certain cells are contained in a given diagram::

        sage: (1, 0) in D
        True
        sage: (2, 2) in D
        False

    If you know that there are entire empty rows or columns at the end of the
    diagram, you can manually pass them with keyword arguments ``n_rows=`` or
    ``n_cols=``::

        sage: Diagram([(0,0), (0,3), (2,2), (2,4)]).pp()
        O . . O .
        . . . . .
        . . O . O
        sage: Diagram([(0,0), (0,3), (2,2), (2,4)], n_rows=6, n_cols=6).pp()
        O . . O . .
        . . . . . .
        . . O . O .
        . . . . . .
        . . . . . .
        . . . . . .

    TESTS::

        sage: from sage.combinat.diagram import Diagrams
        sage: D = Diagrams().an_element()
        sage: TestSuite(D).run()
    """
    @staticmethod
    def __classcall_private__(self, cells, n_rows=None, n_cols=None, check=True):
        r"""
        Normalize the input so that it lives in the correct parent.

        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,0), (0,3), (2,2), (2,4)])
            sage: D.parent()
            Combinatorial diagrams
        """
        return Diagrams()(cells, n_rows, n_cols, check)

    def __init__(self, parent, cells, n_rows=None, n_cols=None, check=True):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D1 = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: D1.cells()
            [(0, 2), (0, 3), (1, 1), (3, 2)]
            sage: D1.nrows()
            4
            sage: D1.ncols()
            4

        We can specify the number of rows and columns explicitly,
        in case they are supposed to be empty::

            sage: D2 = Diagram([(0,2),(0,3),(1,1),(3,2)], n_cols=5)
            sage: D2.cells()
            [(0, 2), (0, 3), (1, 1), (3, 2)]
            sage: D2.ncols()
            5
            sage: D2.pp()
            . . O O .
            . O . . .
            . . . . .
            . . O . .
        """
        self._cells = frozenset(cells)

        if self._cells:
            # minimum possible number of rows/cols
            N_rows = max(c[0] for c in self._cells)
            N_cols = max(c[1] for c in self._cells)
        else: # if there are no cells
            N_rows = 0
            N_cols = 0

        if n_rows is not None:
            if n_rows < N_rows + 1:
                raise ValueError('n_rows is too small')
            self._n_rows = n_rows
        else:
            self._n_rows = N_rows + 1
        if n_cols is not None:
            if n_cols < N_cols + 1:
                raise ValueError('n_cols is too small')
            self._n_cols = n_cols
        else:
            self._n_cols = N_cols + 1

        self._n_nonempty_rows = len(set(i for i, j in self._cells))
        self._n_nonempty_cols = len(set(j for i, j in self._cells))

        ClonableArray.__init__(self, parent, cells, check)

    def _hash_(self):
        r"""
        TESTS::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: hash(D)
            5125392318921082108
        """
        return hash(tuple(sorted(self._cells)))

    def __contains__(self, other):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: (1, 2) in D
            False
            sage: (0, 2) in D
            True
            sage: (2, 1) in D
            False
            sage: (3, 2) in D
            True
        """
        return other in self._cells

    def _repr_(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)]); D
            [(0, 2), (0, 3), (1, 1), (3, 2)]
        """
        return str(sorted(self._cells))

    def pp(self):
        r"""
        Return a visualization of the diagram. Cells which are present in the
        diagram are filled with a ``O``. Cells which are not present in the
        diagram are filled with a ``.``.

        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: Diagram([(0,0), (0,3), (2,2), (2,4)]).pp()
            O . . O .
            . . . . .
            . . O . O
            sage: Diagram([(0,0), (0,3), (2,2), (2,4)], n_rows=6, n_cols=6).pp()
            O . . O . .
            . . . . . .
            . . O . O .
            . . . . . .
            . . . . . .
            . . . . . .
        """
        output_str = ''

        for i in range(self._n_rows):
            for j in range(self._n_cols):
                if (i, j) in self:
                    output_str += 'O '
                else:
                    output_str += '. '
            output_str += '\n'

        print(output_str, end='')  # don't double up on `\n`'ss

    def number_of_rows(self):
        r"""
        Return the total number of rows of the cell, including those which do
        not have any cells.

        EXAMPLES:

        The following example has three rows which are filled, but they
        are contained in rows 0 to 3 (for a total of four)::

            sage: from sage.combinat.diagram import Diagram
            sage: D1 = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: D1.number_of_rows()
            4
            sage: D1.nrows()
            4

        We can also include empty rows at the end::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)], n_rows=6)
            sage: D.number_of_rows()
            6
            sage: D.pp()
            . . O O
            . O . .
            . . . .
            . . O .
            . . . .
            . . . .
        """
        return self._n_rows

    nrows = number_of_rows

    def number_of_cols(self):
        r"""
        Return the total number of rows of the cell, including those which do
        not have any cells.

        EXAMPLES:

        The following example has three columns which are filled, but they
        are contained in rows 0 to 3 (for a total of four)::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: D.number_of_cols()
            4
            sage: D.ncols()
            4

        We can also include empty columns at the end::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,2),(0,3),(1,1),(3,2)], n_cols=6)
            sage: D.number_of_cols()
            6
            sage: D.pp()
            . . O O . .
            . O . . . .
            . . . . . .
            . . O . . .
        """

        return self._n_cols

    ncols = number_of_cols

    def cells(self):
        r"""
        Return a ``list`` of the cells contained in the diagram ``self``.

        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D1 = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: D1.cells()
            [(0, 2), (0, 3), (1, 1), (3, 2)]
        """
        return sorted(self._cells)

    def number_of_cells(self):
        r"""
        Return the total number of cells contained in the diagram ``self``.

        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D1 = Diagram([(0,2),(0,3),(1,1),(3,2)])
            sage: D1.number_of_cells()
            4
            sage: D1.n_cells()
            4
        """
        return len(self._cells)

    n_cells = number_of_cells

    size = number_of_cells

    def check(self):
        r"""
        Check that this is a valid diagram by checking that it is an iterable
        of length-two tuples. (The fact that each tuple is length-two is
        implicitly checked during creation of the diagram).

        .. WARNING::

            This method is required for ``Diagram`` to be a subclass of
            :class:`~sage.structure.list_clone.ClonableArray`, however the check
            is *not* automatically performed upon creation of the element.

        EXAMPLES::

            sage: from sage.combinat.diagram import Diagram
            sage: D = Diagram([(0,0), (0,3), (2,2), (2,4)])
            sage: D.check()

        In the next two examples, a bad diagram is passed.
        The first example fails because one cells is indexed by negative
        integers::

            sage: D = Diagram([(0,0), (0,-3), (2,2), (2,4)])
            Traceback (most recent call last):
            ...
            ValueError: Diagrams must be indexed by non-negative integers

        The next example fails because one cell is indexed by rational
        numbers::

            sage: D = Diagram([(0,0), (0,3), (2/3,2), (2,4)])
            Traceback (most recent call last):
            ...
            ValueError: Diagrams must be indexed by non-negative integers
        """
        from sage.sets.non_negative_integers import NonNegativeIntegers
        NN = NonNegativeIntegers()
        if not all(all(list(i in NN for i in c)) for c in self._cells):
            raise ValueError("Diagrams must be indexed by non-negative integers")


class Diagrams(UniqueRepresentation, Parent):
    r"""
    The class of combinatorial diagrams.

    A *combinatorial diagram* is a set of cells indexed by pairs of natural
    numbers. Calling an instance of :class:`Diagrams` is one way to construct
    diagrams.

    EXAMPLES::

        sage: from sage.combinat.diagram import Diagrams
        sage: Dgms = Diagrams()
        sage: D = Dgms([(0,0), (0,3), (2,2), (2,4)])
        sage: D.parent()
        Combinatorial diagrams

    """
    def __init__(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagrams
            sage: Dgms = Diagrams(); Dgms
            Combinatorial diagrams

        TESTS::

            sage: TestSuite(Dgms).run()
        """

        Parent.__init__(self, category=Sets())

    def _repr_(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagrams
            sage: Dgms = Diagrams(); Dgms
            Combinatorial diagrams
        """
        return 'Combinatorial diagrams'

    def _element_constructor_(self, cells, n_rows=None, n_cols=None, check=True):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagrams
            sage: Dgms = Diagrams()
            sage: Dgms([(0,1),(2,2)]).pp()
            . O .
            . . .
            . . O

        TESTS::

            sage: TestSuite(Dgms).run()
        """
        return self.element_class(self, cells, n_rows, n_cols, check)

    def _an_element_(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import Diagrams
            sage: Dgms = Diagrams()
            sage: D = Dgms.an_element(); D
            [(0, 2), (1, 1), (2, 3)]
            sage: D.pp()
            . . O .
            . O . .
            . . . O
        """
        return self([(0, 2), (1, 1), (2, 3)])

    def from_polyomino(self, p):
        r"""
        Create the diagram corresponding to a 2d
        :class:`~sage.combinat.tiling.Polyomino.`

        EXAMPLES::

            sage: from sage.combinat.tiling import Polyomino
            sage: p = Polyomino([(0,0),(1,0),(1,1),(1,2)])
            sage: from sage.combinat.diagram import Diagrams
            sage: Diagrams().from_polyomino(p).pp()
            O . .
            O O O
            sage: p = Polyomino([(0,0,0), (0,1,0), (1,1,0), (1,1,1)], color='blue')
            sage: Diagrams().from_polyomino(p)
            Traceback (most recent call last):
            ...
            ValueError: Dimension of the polyomino must be 2
        """
        if not p._dimension == 2:
            raise ValueError("Dimension of the polyomino must be 2")
        cells = map(tuple, list(p))
        return self.element_class(self, cells)

    def from_composition(self, alpha):
        r"""
        Create the diagram corresponding to a weak composition `alpha \vDash n`.

        EXAMPLES::

            sage: alpha = Composition([3,0,2,1,4,4])
            sage: from sage.combinat.diagram import Diagrams
            sage: Diagrams().from_composition(alpha).pp()
            O O O .
            . . . .
            O O . .
            O . . .
            O O O O
            O O O O
        """
        cells = []
        for i, n in enumerate(alpha):
            cells.extend((i, j) for j in range(n))
        return self.element_class(self, cells, check=False)

    def from_zero_one_matrix(self, M, check=True):
        r"""
        Get a diagram from a matrix with entries in `\{0, 1\}`, where
        positions of cells are indicated by the `1`'s.

        EXAMPLES::

            sage: M = matrix([[1,0,1,1],[0,1,1,0]])
            sage: from sage.combinat.diagram import Diagrams
            sage: Diagrams().from_zero_one_matrix(M).pp()
            O . O O
            . O O .

            sage: M = matrix([[1, 0, 0], [1, 0, 0], [0, 0, 0]])
            sage: Diagrams().from_zero_one_matrix(M).pp()
            O . .
            O . .
            . . .

        """
        # check matrix is zero-one
        n_rows, n_cols = M.dimensions()

        zero = M.base_ring().zero()
        one = M.base_ring().one()

        if check:
            for i in range(n_rows):
                for j in range(n_cols):
                    if not (M[i,j] == zero or M[i,j] == one):
                        raise ValueError("Matrix entries must be 0 or 1")
        cells = [(i, j) for i in range(n_rows) for j in range(n_cols) if M[i,j]]

        return self.element_class(self, cells, n_rows, n_cols, check=False)

    Element = Diagram


####################
# Northwest diagrams
####################

class NorthwestDiagram(Diagram, metaclass=InheritComparisonClasscallMetaclass):
    r"""
    A diagram is a set of cells indexed by natural numbers. Such a diagram
    has the *northwest property* if the presence of cells `(i1, j1)` and
    `(i2, j2)` implies the presence of the cell
    `(\min(i1, i2), \min(j1, j2))`. Diagrams with the northwest property are
    called *northwest diagrams*.

    For general diagrams see :class:`Diagram`.

    EXAMPLES::

        sage: from sage.combinat.diagram import NorthwestDiagram
        sage: N = NorthwestDiagram([(0,0), (0, 2), (2,0)])

    To visualize them, use the ``.pp()`` method::

        sage: N.pp()
        O . O
        . . .
        O . .
    """
    @staticmethod
    def __classcall_private__(self, cells, n_rows=None,
                              n_cols=None, check=True):
        """
        Normalize input to ensure a correct parent. This method also allows
        one to specify whether or not to check the northwest property for the
        provided cells.

        EXAMPLES::

            sage: from sage.combinat.diagram import NorthwestDiagram, NorthwestDiagrams
            sage: N1 = NorthwestDiagram([(0,1), (0,2)])
            sage: N2 = NorthwestDiagram([(0,1), (0,3)])
            sage: N1.parent() is N2.parent()
            True
            sage: N3 = NorthwestDiagrams()([(0,1), (0,2)])
            sage: N3.parent() is NorthwestDiagrams()
            True
            sage: N1.parent() is NorthwestDiagrams()
            True
        """
        return NorthwestDiagrams()(cells, n_rows, n_cols, check)

    def check(self):
        r"""
        A diagram has the northwest property if the presence of cells
        `(i1, j1)` and `(i2, j2)` implies the presence of the cell
        `(min(i1, i2), min(j1, j2))`. This method checks if the northwest
        property is satisfied for ``self``

        EXAMPLES::

            sage: from sage.combinat.diagram import NorthwestDiagram
            sage: N = NorthwestDiagram([(0,0), (0,3), (3,0)])
            sage: N.check()

        Here is a non-example::

            sage: notN = NorthwestDiagram([(0,1), (1,0)])  #.check() is implicit
            Traceback (most recent call last):
            ...
            ValueError: diagram is not northwest

        TESTS::

            sage: NorthwestDiagram([(0,1/2)])
            Traceback (most recent call last):
            ...
            ValueError: Diagrams must be indexed by non-negative integers
        """
        from itertools import combinations
        Diagram.check(self)
        if not all((min(i1, i2), min(j1, j2)) in self
                   for (i1, j1), (i2, j2) in combinations(self._cells, 2)):
            raise ValueError("diagram is not northwest")

    def peelable_tableaux(self):
        r"""
        For a fixed northwest diagram `D`, we say that a Young tableau `T` is
        `D`-peelable if:

        - the row indices of the cells in the first column of `D` are
        the entries in an initial segment in the first column of `T` and

        - the tableau `Q` obtained by removing those cells from `T` and playing
        jeu de taquin is `D-C`-peelable, where `D-C` is the diagram formed by
        forgetting the first column of `D`.

        Reiner and Shimozono [RS1995]_ showed that the number
        `\operatorname{red}(w)` of reduced words of a permutation `w` may be
        computed using the peelable tableaux of the Rothe diagram `D(w)`.
        Explicitly,

        .. MATH::

            \operatorname{red}(w) = \sum_{T} f_{\operatorname{shape} T}

        where the sum runs over the `D(w)`-peelable tableaux `T` and `f_\lambda`
        is the number of standard Young tableaux of shape `\lambda` (which may
        be computed using the hook-length formula).

        EXAMPLES:

        We can compute the `D`-peelable diagrams for a northwest diagram `D`::

            sage: from sage.combinat.diagram import NorthwestDiagram
            sage: cells = [(0,0), (0,1), (0,2), (1,0), (2,0), (2,2), (2,4),
            ....:          (4,0), (4,2)]
            sage: D = NorthwestDiagram(cells); D.pp()
            O O O . .
            O . . . .
            O . O . O
            . . . . .
            O . O . .
            sage: D.peelable_tableaux()
            {[[1, 1, 1], [2, 3, 3], [3, 5], [5]],
            [[1, 1, 1, 3], [2, 3], [3, 5], [5]]}

        EXAMPLES:

        If the diagram is only one column, there is only one peelable tableau::

            sage: from sage.combinat.diagram import NorthwestDiagram
            sage: NWD = NorthwestDiagram([(0,0), (2,0)])
            sage: NWD.peelable_tableaux()
            {[[1], [3]]}

        From [RS1995]_ we know that there is only one peelable tableau for the
        Rothe diagram of the permutation (in one line notation) `251643`::

            sage: D = NorthwestDiagram([(1, 2), (1, 3), (3, 2), (3, 3), (4, 2)])
            sage: D.pp()
            . . . .
            . . O O
            . . . .
            . . O O
            . . O .

            sage: D.peelable_tableaux()
            {[[2, 2], [4, 4], [5]]}

        Here are all the intermediate steps to compute the peelables for the
        Rothe diagram of (in one-line notation) `64817235`. They are listed from
        deepest in the recursion to the final step. The recursion has depth five
        in this case so we will label the intermediate tableaux by `D_i` where
        `i` is the step in the recursion at which they appear.

        Start with the one that has a single column::

            sage: D5 = NorthwestDiagram([(2,0)]); D5.pp()
            .
            .
            O
            sage: D5.peelable_tableaux()
            {[[3]]}

        Now we know all of the `D_5` peelables, so we can compute the `D_4`
        peelables.

            sage: D4 = NorthwestDiagram([(0, 0), (2,0), (4, 0), (2, 2)])
            sage: D4.pp()
            O . .
            . . .
            O . O
            . . .
            O . .

            sage: D4.peelable_tableaux()
            {[[1, 3], [3], [5]]}

        There is only one `D_4` peelable, so we can compute the `D_3`
        peelables::

            sage: D3 = NorthwestDiagram([(0,0), (0,1), (2, 1), (2, 3), (4,1)])
            sage: D3.pp()
            O O . .
            . . . .
            . O . O
            . . . .
            . O . .

            sage: D3.peelable_tableaux()
            {[[1, 1], [3, 3], [5]], [[1, 1, 3], [3], [5]]}

        Now compute the `D_2` peelables::

            sage: cells = [(0,0), (0,1), (0,2), (1,0), (2,0), (2,2), (2,4),
            ....:          (4,0), (4,2)]
            sage: D2 = NorthwestDiagram(cells); D2.pp()
            O O O . .
            O . . . .
            O . O . O
            . . . . .
            O . O . .

            sage: D2.peelable_tableaux()
            {[[1, 1, 1], [2, 3, 3], [3, 5], [5]],
            [[1, 1, 1, 3], [2, 3], [3, 5], [5]]}

        And the `D_1` peelables::

            sage: cells = [(0,0), (0,1), (0,2), (0,3), (1,0), (1,1), (2,0),
            ....:          (2,1), (2,3), (2,5), (4,0), (4,1), (4,3)]
            sage: D1 = NorthwestDiagram(cells); D1.pp()
            O O O O . .
            O O . . . .
            O O . O . O
            . . . . . .
            O O . O . .

            sage: D1.peelable_tableaux()
            {[[1, 1, 1, 1], [2, 2, 3, 3], [3, 3, 5], [5, 5]],
            [[1, 1, 1, 1, 3], [2, 2, 3], [3, 3, 5], [5, 5]]}

        Which we can use to get the `D` peelables::

            sage: cells = [(0,0), (0,1), (0,2), (0,3), (0,4),
            ....:          (1,0), (1,1), (1,2),
            ....:          (2,0), (2,1), (2,2), (2,4), (2,6),
            ....:                 (4,1), (4,2), (4,4)]
            sage: D = NorthwestDiagram(cells); D.pp()
            O O O O O . .
            O O O . . . .
            O O O . O . O
            . . . . . . .
            . O O . O . .
            sage: D.peelable_tableaux()
            {[[1, 1, 1, 1, 1], [2, 2, 2, 3, 3], [3, 3, 3], [5, 5, 5]],
             [[1, 1, 1, 1, 1], [2, 2, 2, 3, 3], [3, 3, 3, 5], [5, 5]],
             [[1, 1, 1, 1, 1, 3], [2, 2, 2, 3], [3, 3, 3], [5, 5, 5]],
             [[1, 1, 1, 1, 1, 3], [2, 2, 2, 3], [3, 3, 3, 5], [5, 5]]}

        .. ALGORITHM::

            This implementation uses the algorithm suggested in remark 25
            of [RS1995]_.
        """
        # TODO: There is a condition on the first column (if the rows in Dhat
        # are a subset of the rows in the first column) which simplifies the
        # description without performing JDT, so we should implement that

        # if there is a single column in the diagram then there is only
        # one posslbe peelable tableau.
        if self._n_nonempty_cols == 1:
            return {Tableau([[i+1] for i, j in self.cells()])}

        first_col = min(j for i, j in self._cells)

        # TODO: The next two lines of code could be optimized by only
        # looping over self._cells once (rather than two separate times)
        # get the diagram without the first column
        Dhat = NorthwestDiagram([c for c in self._cells if c[1] != first_col])

        # get the values from the first column
        new_vals = sorted(i + 1 for i, j in self._cells if j == first_col)

        k = self.n_cells() - Dhat.n_cells()

        peelables = set()

        for Q in Dhat.peelable_tableaux():
            # get the vertical strips
            mu = Q.shape()
            vertical_strip_cells = mu.vertical_border_strip_cells(k)
            for s in vertical_strip_cells:
                sQ = SkewTableaux()(Q)  # sQ is skew - get it?
                # perform the jeu de taquin slides
                for c in s:
                    sQ = sQ.backward_slide(c)
                # create the new tableau by filling the columns
                sQ_new = sQ.to_list()
                for n in range(k):
                    sQ_new[n][0] = new_vals[n]

                T = Tableau(sQ_new)
                if T.is_column_strict():
                    peelables.add(T)

        return peelables


class NorthwestDiagrams(Diagrams):
    r"""
    Diagrams satisfying the northwest property.

    A diagram is a
    *northwest diagram* if it satsifies the property that: the presence of two
    cells `(i_1, j_1)` and `(i_2, j_2)` in a diagram `D` implies the presence of
    the cell `(\min(i_1, i_2), \min(j_1, j_2))`.

    EXAMPLES::

        sage: from sage.combinat.diagram import NorthwestDiagram
        sage: N = NorthwestDiagram([(0,0), (0, 10), (5,0)]); N.pp()
        O . . . . . . . . . O
        . . . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        O . . . . . . . . . .

    Note that checking whether or not the northwest property is satisfied is
    automatically checked. The diagram found by adding the cell `(1,1)` to the
    diagram above is *not* a northwest diagram. The cell `(1,0)` should be
    present due to the presence of `(5,0)` and `(1,1)`::

        sage: from sage.combinat.diagram import Diagram
        sage: Diagram([(0, 0), (0, 10), (5, 0), (1, 1)]).pp()
        O . . . . . . . . . O
        . O . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        O . . . . . . . . . .
        sage: NorthwestDiagram([(0, 0), (0, 10), (5, 0), (1, 1)])
        Traceback (most recent call last):
        ...
        ValueError: diagram is not northwest

    However, this behavior can be turned off if you are confident that you are
    providing a northwest diagram::

        sage: N = NorthwestDiagram([(0, 0), (0, 10), (5, 0),
        ....:                      (1, 1), (0, 1), (1, 0)],
        ....:                      check=False)
        sage: N.pp()
        O O . . . . . . . . O
        O O . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        O . . . . . . . . . .

    Note that arbitrary diagrams which happen to be northwest diagrams only live
    in the parent of :class:`Diagrams`::

        sage: D = Diagram([(0, 0), (0, 10), (5, 0), (1, 1), (0, 1), (1, 0)])
        sage: D.pp()
        O O . . . . . . . . O
        O O . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        . . . . . . . . . . .
        O . . . . . . . . . .
        sage: from sage.combinat.diagram import NorthwestDiagrams
        sage: D in NorthwestDiagrams()
        False

    Here are some more examples::

        sage: from sage.combinat.diagram import NorthwestDiagram, NorthwestDiagrams
        sage: D = NorthwestDiagram([(0,1), (0,2), (1,1)]); D.pp()
        . O O
        . O .
        sage: NWDgms = NorthwestDiagrams()
        sage: D = NWDgms([(1,1), (1,2), (2,1)]); D.pp()
        . . .
        . O O
        . O .
        sage: D.parent()
        Combinatorial northwest diagrams

    Additionally, there are natural constructions of a northwest diagram
    given the data of a permutation (Rothe diagrams are the protypical example
    of northwest diagrams), or the data of a partition of an integer, or a
    skew partition.

    The Rothe diagram `D(\omega)` of a permutation `\omega` is specified by
    the cells

    .. MATH::

        D(\omega) = \{(\omega_j, i) : i<j,\, \omega_i > \omega_j \}.

    We can construct one by calling :meth:`rothe_diagram` method on the parent
    class :class:`NorthwestDiagrams`::

        sage: w = Permutations(4)([4,3,2,1])
        sage: NorthwestDiagrams().rothe_diagram(w).pp()
        O O O .
        O O . .
        O . . .
        . . . .

    To turn a Ferrers diagram into a northwest diagram, we may call the
    :meth:`from_partition` method. This will return a Ferrer's diagram in the
    parent of all northwest diagrams. For many use-cases it is probably better
    to get Ferrer's diagrams by the corresponding method on partitons, namely
    :meth:`sage.combinat.partitions.Partitions.ferrers_diagram`::

        sage: mu = Partition([7,3,1,1])
        sage: mu.pp()
        *******
        ***
        *
        *
        sage: NorthwestDiagrams().from_partition(mu).pp()
        O O O O O O O
        O O O . . . .
        O . . . . . .
        O . . . . . .

    It is also possible to turn a Ferrers diagram of a skew partition into a
    northwest diagram, altough it is more subtle than just using the skew
    diagram itself. One must first reflect the partition about a vertical axis
    so that the skew partition looks "backwards"::

        sage: mu, nu = Partition([5,4,3,2,1]), Partition([3,2,1])
        sage: s = mu/nu; s.pp()
           **
          **
         **
        **
        *
        sage: NorthwestDiagrams().from_skew_partition(s).pp()
        O O . . .
        . O O . .
        . . O O .
        . . . O O
        . . . . O
    """

    def _repr_(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: NWDgms = NorthwestDiagrams(); NWDgms
            Combinatorial northwest diagrams
        """
        return 'Combinatorial northwest diagrams'

    def _an_element_(self):
        r"""
        EXAMPLES::

            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: NWDgms = NorthwestDiagrams()
            sage: NWD = NWDgms.an_element(); NWD
            [(0, 1), (0, 2), (1, 1), (2, 3)]
            sage: NWD.pp()
            . O O .
            . O . .
            . . . O
            sage: NWD.parent() is NWDgms
            True
        """
        return self([(0, 1), (0, 2), (1, 1), (2, 3)])

    def rothe_diagram(self, w):
        r"""
        Return the Rothe diagram of ``w``.

        One particular way of constructing a northwest diagram from a permutation is
        by constructing its Rothe diagram. Formally, if `\omega` is a permutation,
        then the Rothe diagram `D(\omega)` is the diagram whose cells are

        .. MATH::

            D(\omega) = \{(\omega_j, i) : i<j,\, \omega_i > \omega_j \}.

        Informally, one can construct the Rothe diagram by starting with all
        `n^2` possible cells, and then deleting the cells `(i, \omega(i))` as
        well as all cells to the right and below. (These are sometimes called
        "death rays".) To compute a Rothe diagram in Sage, start with a
        :class:`~sage.combinat.permutation.Permutation`::

            sage: w = Permutations(8)([2,5,4,1,3,6,7,8])

        Then call :func:`RotheDiagram` on ``w``::

            sage: from sage.combinat.diagram import RotheDiagram
            sage: RotheDiagram(w).pp()
            O . . . . . . .
            O . O O . . . .
            O . O . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .

        EXAMPLES::

            sage: w = Permutations(3)([2,1,3])
            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: NorthwestDiagrams().rothe_diagram(w).pp()
            O . .
            . . .
            . . .
            sage: NorthwestDiagrams().from_permutation(w).pp()
            O . .
            . . .
            . . .
        """
        return RotheDiagram(w)

    from_permutation = rothe_diagram

    def from_partition(self, mu):
        r"""
        Return the Ferrer's diagram of ``mu`` as an element of the parent
        ``NorthwestDiagrams``

        EXAMPLES::

            sage: mu = Partition([5,2,1]); mu.pp()
            *****
            **
            *
            sage: mu.parent()
            Partitions
            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: D = NorthwestDiagrams().from_partition(mu)
            sage: D.pp()
            O O O O O
            O O . . .
            O . . . .
            sage: D.parent()
            Combinatorial northwest diagrams

        This will print in English notation even if the notation is set to
        French for the partition.

            sage: Partitions.options.convention="french"
            sage: mu.pp()
            *
            **
            *****
            sage: D.pp()
            O O O O O
            O O . . .
            O . . . .

        TESTS::

            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: mu = [5, 2, 1]
            sage: D = NorthwestDiagrams().from_partition(mu)
            Traceback (most recent call last):
            ...
            ValueError: mu must be a Partition
        """
        if not isinstance(mu, Partition):
            raise ValueError("mu must be a Partition")
        return self.element_class(self, mu.cells(), check=False)

    def from_skew_partition(self, s):
        r"""
        Get the northwest diagram found by reflecting a skew shape across
        a vertical plane.

        EXAMPLES::

            sage: mu, nu = Partition([3,2,1]), Partition([2,1])
            sage: s = mu/nu; s.pp()
              *
             *
            *
            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: D = NorthwestDiagrams().from_skew_partition(s)
            sage: D.pp()
            O . .
            . O .
            . . O

            sage: mu, nu = Partition([3,3,2]), Partition([2,2,2])
            sage: s = mu/nu; s.pp()
              *
              *
            sage: NorthwestDiagrams().from_skew_partition(s).pp()
            O . .
            O . .
            . . .

        TESTS::

            sage: mu = Partition([3,2,1])
            sage: NorthwestDiagrams().from_skew_partition(mu)
            Traceback (most recent call last):
            ...
            ValueError: mu must be a SkewPartition
        """
        if not isinstance(s, SkewPartition):
            raise ValueError("mu must be a SkewPartition")

        n_cols = s.outer()[0]
        n_rows = len(s.outer())

        cells = [(i, n_cols - 1 - j) for i, j in s.cells()]

        return self.element_class(self, cells, n_rows, n_cols, check=False)

    def from_parallelogram_polyomino(self, p):
        r"""
        Create the diagram corresponding to a
        :class:`~sage.combinat.parallelogram_polyomino.ParallelogramPolyomino`.

        EXAMPLES::

            sage: p = ParallelogramPolyomino([[0, 0, 1, 0, 0, 0, 1, 1],
            ....:                              [1, 1, 0, 1, 0, 0, 0, 0]])
            sage: from sage.combinat.diagram import NorthwestDiagrams
            sage: NorthwestDiagrams().from_parallelogram_polyomino(p).pp()
            O O .
            O O O
            . O O
            . O O
            . O O
        """
        from sage.matrix.constructor import Matrix
        M = Matrix(p.get_array())
        return self.from_zero_one_matrix(M)

    Element = NorthwestDiagram


def RotheDiagram(w):
    r"""
    A constructor to build the Rothe diagram of a permutation w as an element
    in the parent of :class:`NorthwestDiagrams`.

    EXAMPLES::

        sage: w = Permutations(9)([1, 7, 4, 5, 9, 3, 2, 8, 6])
        sage: from sage.combinat.diagram import RotheDiagram
        sage: D = RotheDiagram(w); D.pp()
        . . . . . . . . .
        . O O O O O . . .
        . O O . . . . . .
        . O O . . . . . .
        . O O . . O . O .
        . O . . . . . . .
        . . . . . . . . .
        . . . . . O . . .
        . . . . . . . . .

    Currently, only elements of the parent
    :class:`sage.combinat.permutations.Permutations` are supported. In
    particular, elements of permutation groups are not supported::

        sage: w = SymmetricGroup(9).an_element()
        sage: RotheDiagram(w)
        Traceback (most recent call last):
        ...
        ValueError: w must be a Permutation


    TESTS::

        sage: w = Permutations(5)([1,2,3,4,5])
        sage: from sage.combinat.diagram import RotheDiagram
        sage: RotheDiagram(w).pp()
        . . . . .
        . . . . .
        . . . . .
        . . . . .
        . . . . .
    """

    from sage.misc.mrange import cartesian_product_iterator

    if w not in Permutations():
        raise ValueError('w must be a Permutation')

    N = w.size()

    cells = [c for c in cartesian_product_iterator((range(N), range(N)))
             if c[0]+1 < w.inverse()(c[1]+1) and c[1]+1 < w(c[0]+1)]

    return NorthwestDiagram(cells, n_rows=N, n_cols=N, check=False)
