# § 2.1. Linear Algebra

!!! definition "Definition 2.1.1 : Complex Vector Space"
    The vector space of most interest to us is $\mathbf{C}^{n}$, the space of all $n$-tuples of complex numbers, $\left(z_{1}, \ldots, z_{n}\right)$.

!!! concept "Concept 2.1.2 : Notation for vectors"
    The elements of a vector space are called **vectors**. We will sometimes use the column matrix notation

    $$
    \left[\begin{array}{c}
    z_{1}  \tag{2.1}\\
    \vdots \\
    z_{n}
    \end{array}\right]
    $$

    to indicate a vector.

    Quantum mechanics is our main motivation for studying linear algebra, so we will also use the standard quantum mechanical notation for a vector in a vector space:

    $$
    \begin{equation*}
    |\psi\rangle . \tag{2.4}
    \end{equation*}
    $$

    Here, $\psi$ is a label for the vector. Any label is valid, although we prefer simple labels like $\psi$ and $\varphi$. The $|\cdot\rangle$ notation indicates that the object is a vector, and the entire object $|\psi\rangle$ is sometimes called a ket.

!!! definition "Definition 2.1.3 : Zero Vector"
    A vector space also contains a special **zero vector**, which we denote by $0$.

    It satisfies the property that for any other vector $|v\rangle$,
    $$
    |v\rangle + 0 = |v\rangle.
    $$

    We do not use ket notation for the zero vector. This is the only exception, because it is conventional to use the notation $|0\rangle$ to mean something else entirely.

    The scalar multiplication operation is such that
    $$
    z 0 = 0
    $$
    for any complex number $z$.

!!! definition "Definition 2.1.4 : vector subspace"
    A **vector subspace** of a vector space $V$ is a subset $W$ of $V$ such that $W$ is also a vector space. That is, $W$ must be closed under scalar multiplication and addition.

## 2.1.1 Bases and Linear Independence

!!! definition "Definition 2.1.5 : Spanning Set"
    A **spanning set** for a vector space is a set of vectors $\left|v_{1}\right\rangle, \ldots,\left|v_{n}\right\rangle$ such that any vector $|v\rangle$ in the vector space can be written as a **linear combination**
    
    $$
    |v\rangle=\sum_{i} a_{i}\left|v_{i}\right\rangle
    $$
    
    of vectors in that set.

    When this happens, we say that the vectors $\left|v_{1}\right\rangle, \ldots,\left|v_{n}\right\rangle$ **span** the vector space.

    For example, a spanning set for the vector space $\mathbf{C}^{2}$ is the set

    $$
    \left|v_{1}\right\rangle \equiv\left[\begin{array}{l}
    1 \\
    0
    \end{array}\right] ; \quad\left|v_{2}\right\rangle \equiv\left[\begin{array}{l}
    0 \\
    1
    \end{array}\right]
    $$

    since any vector

    $$
    |v\rangle=\left[\begin{array}{l}
    a_{1} \\
    a_{2}
    \end{array}\right]
    $$

    in $\mathbf{C}^{2}$ can be written as the linear combination $|v\rangle=a_{1}\left|v_{1}\right\rangle+a_{2}\left|v_{2}\right\rangle$.

!!! example "Example 2.1.6 : Two Different Spanning Sets for $\mathbf{C}^{2}$"
    A spanning set for the vector space $\mathbf{C}^{2}$ is the set

    $$
    \left|v_{1}\right\rangle \equiv\left[\begin{array}{l}
    1 \\
    0
    \end{array}\right] ; \quad\left|v_{2}\right\rangle \equiv\left[\begin{array}{l}
    0 \\
    1
    \end{array}\right]
    $$

    since any vector

    $$
    |v\rangle=\left[\begin{array}{l}
    a_{1} \\
    a_{2}
    \end{array}\right]
    $$

    in $\mathbf{C}^{2}$ can be written as a linear combination,

    $$
    |v\rangle=a_{1}\left|v_{1}\right\rangle+a_{2}\left|v_{2}\right\rangle.
    $$

    Thus $\left|v_{1}\right\rangle$ and $\left|v_{2}\right\rangle$ span the vector space $\mathbf{C}^{2}$.

    A vector space may have many different spanning sets. A second spanning set for $\mathbf{C}^{2}$ is the set

    $$
    \left|v_{1}\right\rangle \equiv \frac{1}{\sqrt{2}}\left[\begin{array}{l}
    1 \\
    1
    \end{array}\right] ; \quad\left|v_{2}\right\rangle \equiv \frac{1}{\sqrt{2}}\left[\begin{array}{r}
    1 \\
    -1
    \end{array}\right]
    $$

    since an arbitrary vector $|v\rangle=\left(a_{1}, a_{2}\right)$ can be written as a linear combination of $\left|v_{1}\right\rangle$ and $\left|v_{2}\right\rangle$,

    $$
    |v\rangle=\frac{a_{1}+a_{2}}{\sqrt{2}}\left|v_{1}\right\rangle+\frac{a_{1}-a_{2}}{\sqrt{2}}\left|v_{2}\right\rangle .
    $$

!!! definition "Definition 2.1.7 : Linearly Dependent, Linearly Independent, Basis, and Dimension"
    A set of non-zero vectors $\left|v_{1}\right\rangle, \ldots, \left|v_{n}\right\rangle$ are **linearly dependent** if there exists a set of complex numbers $a_{1}, \ldots, a_{n}$ with $a_{i} \neq 0$ for at least one value of $i$, such that

    $$
    a_{1}\left|v_{1}\right\rangle+a_{2}\left|v_{2}\right\rangle+\cdots+a_{n}\left|v_{n}\right\rangle=0 \tag{2.9}
    $$

    A set of vectors is **linearly independent** if it is not linearly dependent.

    Any two sets of linearly independent vectors which span a vector space $V$ contain the same number of elements. We call such a set a **basis** for $V$. Furthermore, such a basis set always exists.

    The number of elements in the basis is defined to be the **dimension** of $V$. In this book we will only be interested in finite dimensional vector spaces.

## Linear Operators and Matrices

!!! definition "Definition 2.1.8 : Linear Operator"
    A **linear operator** between vector spaces $V$ and $W$ is any function $A: V \rightarrow W$ which is linear in its inputs,

    $$
    A\left(\sum_{i} a_{i}\left|v_{i}\right\rangle\right)=\sum_{i} a_{i} A\left(\left|v_{i}\right\rangle\right) . \tag{2.10}
    $$

    Usually we write $A|v\rangle$ to denote $A(|v\rangle)$.

    When we say that a linear operator $A$ is defined on a vector space $V$, we mean that $A$ is a linear operator from $V$ to $V$.

    An important linear operator on any vector space $V$ is the **identity operator**, $I_{V}$, defined by the equation $I_{V}|v\rangle \equiv|v\rangle$ for all vectors $|v\rangle$.
    Where no chance of confusion arises we drop the subscript $V$ and just write $I$ to denote the identity operator.

    Another important linear operator is the **zero operator**, which we denote $0$.
    The zero operator maps all vectors to the zero vector, $0|v\rangle \equiv 0$.

!!! definition "Definition 2.1.9 : Composition of Operators"
    Suppose $V, W$, and $X$ are vector spaces, and $A: V \rightarrow W$ and $B: W \rightarrow X$ are linear operators.
    Then we use the notation $B A$ to denote the composition of $B$ with $A$, defined by

    $$
    (B A)(|v\rangle) \equiv B(A(|v\rangle)).
    $$

!!! concept "Concept 2.1.10 : Matrix representation"
    The most convenient way to understand linear operators is in terms of their matrix representations.
    In fact, the linear operator and matrix viewpoints are completely equivalent, and we will use the matrix representation and abstract operator viewpoints interchangeably.

    An $m$ by $n$ complex matrix $A$ with entries $A_{i j}$ may be regarded as a linear operator sending vectors in the vector space $\mathbf{C}^{n}$ to the vector space $\mathbf{C}^{m}$, under matrix multiplication of the matrix $A$ by a vector in $\mathbf{C}^{n}$.
    More precisely, the claim that the matrix $A$ is a linear operator means that

    $$
    A\left(\sum_{i} a_{i}\left|v_{i}\right\rangle\right)=\sum_{i} a_{i} A\left|v_{i}\right\rangle
    $$

    is true as an equation where the operation is matrix multiplication of $A$ by column vectors.

    Conversely, suppose $A: V \rightarrow W$ is a linear operator, $\left|v_{1}\right\rangle, \ldots,\left|v_{m}\right\rangle$ is a basis for $V$, and $\left|w_{1}\right\rangle, \ldots,\left|w_{n}\right\rangle$ is a basis for $W$.
    Then for each $j$ in the range $1, \ldots, m$, there exist complex numbers $A_{1 j}$ through $A_{n j}$ such that

    $$
    A\left|v_{j}\right\rangle=\sum_{i} A_{i j}\left|w_{i}\right\rangle
    $$

    The matrix whose entries are the values $A_{i j}$ is said to form a matrix representation of the operator $A$.
    Note that to make the connection between matrices and linear operators we must specify a set of input and output basis states for the input and output vector spaces of the linear operator.

## The Pauli Matrices

!!! definition "Definition 2.1.11 : The Pauli matrices"
    The **Pauli matrices** are the following $2$ by $2$ matrices:

    $$
    \begin{aligned}
    \sigma_{0} \equiv I \equiv\left[\begin{array}{ll}
    1 & 0 \\
    0 & 1
    \end{array}\right] & \sigma_{1} \equiv \sigma_{x} \equiv X \equiv\left[\begin{array}{ll}
    0 & 1 \\
    1 & 0
    \end{array}\right] \\
    \sigma_{2} \equiv \sigma_{y} \equiv Y \equiv\left[\begin{array}{rr}
    0 & -i \\
    i & 0
    \end{array}\right] & \sigma_{3} \equiv \sigma_{z} \equiv Z \equiv\left[\begin{array}{rr}
    1 & 0 \\
    0 & -1
    \end{array}\right]
    \end{aligned}
    $$

    These matrices go by a variety of notations. Sometimes $I$ is omitted from the list, with just $X$, $Y$, and $Z$ known as the Pauli matrices.

## Inner Products

!!! definition "Definition 2.1.12 : Inner Product"
    An **inner product** on a vector space $V$ is a function $(\cdot, \cdot)$ from $V \times V$ to $\mathbf{C}$ that takes two vectors $|v\rangle$ and $|w\rangle$ as input and produces a complex number as output.

    For pedagogical clarity, we will sometimes write the inner product as $(|v\rangle,|w\rangle)$.
    The standard quantum mechanical notation for this inner product is $\langle v \mid w\rangle$.
    In that notation, $\langle v|$ denotes the dual vector to $|v\rangle$, viewed as a linear operator from the inner product space $V$ to the complex numbers $\mathbf{C}$, and

    $$
    \langle v|(|w\rangle) \equiv \langle v \mid w\rangle \equiv (|v\rangle,|w\rangle).
    $$

    A function $(\cdot, \cdot)$ from $V \times V$ to $\mathbf{C}$ is an inner product if it satisfies the following requirements:

    1. $(\cdot, \cdot)$ is linear in the second argument:

    $$
    \left(|v\rangle, \sum_{i} \lambda_{i}\left|w_{i}\right\rangle\right)=\sum_{i} \lambda_{i}\left(|v\rangle,\left|w_{i}\right\rangle\right) . \tag{2.13}
    $$

    2. $(|v\rangle,|w\rangle)=(|w\rangle,|v\rangle)^{*}$.

    3. $(|v\rangle,|v\rangle) \geq 0$ with equality if and only if $|v\rangle=0$.

    A vector space equipped with an inner product is called an **inner product space**.

!!! definition "Definition 2.1.13 : Dual Vector"
    In the standard quantum mechanical notation, the inner product $(|v\rangle,|w\rangle)$ is written as $\langle v \mid w\rangle$, where $|v\rangle$ and $|w\rangle$ are vectors in the inner product space $V$.
    The notation $\langle v|$ is used for the **dual vector** to the vector $|v\rangle$; the dual is a linear operator from the inner product space $V$ to the complex numbers $\mathbf{C}$, defined by

    $$
    \langle v|(|w\rangle) \equiv \langle v \mid w\rangle \equiv (|v\rangle,|w\rangle).
    $$

!!! theorem "Theorem 2.1.14 : Conjugate-Linearity in the First Argument"
    Any inner product $(\cdot, \cdot)$ is conjugate-linear in the first argument:

    $$
    \left(\sum_{i} \lambda_{i}\left|w_{i}\right\rangle,|v\rangle\right)=\sum_{i} \lambda_{i}^{*}\left(\left|w_{i}\right\rangle,|v\rangle\right) .
    $$

!!! example "Example 2.1.15 : Inner product on $\mathbf{C}^{n}$"
    For example, $\mathbf{C}^{n}$ has an inner product defined by

    $$
    \left(\left(y_{1}, \ldots, y_{n}\right),\left(z_{1}, \ldots, z_{n}\right)\right) \equiv \sum_{i} y_{i}^{*} z_{i}=\left[y_{1}^{*} \ldots y_{n}^{*}\right]\left[\begin{array}{c}
    z_{1} \\
    \vdots \\
    z_{n}
    \end{array}\right]
    $$

!!! concept "Concept 2.1.16 : Hilbert space"
    Discussions of quantum mechanics often refer to Hilbert space.
    In the finite-dimensional complex vector spaces used in quantum computation and quantum information, a Hilbert space is exactly the same as an inner product space.
    For this reason, we use the two terms interchangeably and usually prefer the term Hilbert space.

    In infinite dimensions, Hilbert spaces satisfy additional technical restrictions beyond those of inner product spaces, but we will not need those restrictions here.

!!! definition "Definition 2.1.17 : Orthogonal, Norm, Unit Vector, Normalized, and Orthonormal Set"
    Vectors $|w\rangle$ and $|v\rangle$ are **orthogonal** if their inner product is zero.
    For example, $|w\rangle \equiv (1,0)$ and $|v\rangle \equiv(0,1)$ are orthogonal with respect to the inner product in **Definition 2.1.12**.

    We define the **norm** of a vector $|v\rangle$ by

    $$
    \||v\rangle \| \equiv \sqrt{\langle v \mid v\rangle} . \tag{2.16}
    $$

    A **unit vector** is a vector $|v\rangle$ such that $\||v\rangle \|=1$.
    We also say that $|v\rangle$ is **normalized** if $\||v\rangle \|=1$.
    For any non-zero vector $|v\rangle$, the vector $|v\rangle / \||v\rangle \|$ is the normalized form of $|v\rangle$.

    A set $\{|i\rangle\}$ of vectors with index $i$ is **orthonormal** if each vector is a unit vector, and distinct vectors in the set are orthogonal; that is, $\langle i \mid j\rangle=\delta_{i j}$, where $i$ and $j$ are both chosen from the index set.

!!! theorem "Theorem 2.1.18 : Gram-Schmidt procedure"
    Suppose $\left|w_{1}\right\rangle, \ldots,\left|w_{d}\right\rangle$ is a basis set for some vector space $V$ with an inner product.
    The Gram-Schmidt procedure produces an orthonormal basis set $\left|v_{1}\right\rangle, \ldots,\left|v_{d}\right\rangle$ for $V$ by defining $\left|v_{1}\right\rangle \equiv\left|w_{1}\right\rangle / \|\left|w_{1}\right\rangle \|$, and for $1 \leq k \leq d-1$ defining $\left|v_{k+1}\right\rangle$ inductively by

    $$
    \left|v_{k+1}\right\rangle \equiv \frac{\left|w_{k+1}\right\rangle-\sum_{i=1}^{k}\left\langle v_{i} \mid w_{k+1}\right\rangle\left|v_{i}\right\rangle}{\|\left|w_{k+1}\right\rangle-\sum_{i=1}^{k}\left\langle v_{i} \mid w_{k+1}\right\rangle\left|v_{i}\right\rangle \|}.
    $$

    The vectors $\left|v_{1}\right\rangle, \ldots,\left|v_{d}\right\rangle$ form an orthonormal set which is also a basis for $V$.
    Thus any finite dimensional vector space of dimension $d$ has an orthonormal basis, $\left|v_{1}\right\rangle, \ldots,\left|v_{d}\right\rangle$.

From now on, when we speak of a **matrix representation** for a linear operator, we mean a matrix representation with respect to orthonormal input and output bases.

!!! theorem "Theorem 2.1.19 : matrix representation of inner product and dual vector"
    Let $|w\rangle=\sum_{i} w_{i}|i\rangle$ and $|v\rangle=\sum_{j} v_{j}|j\rangle$ be representations of vectors $|w\rangle$ and $|v\rangle$ with respect to some orthonormal basis $|i\rangle$ of a Hilbert space. Then, since $\langle i \mid j\rangle=\delta_{i j}$,

    $$
    \begin{align*}
    \langle v \mid w\rangle & =\left(\sum_{i} v_{i}|i\rangle, \sum_{j} w_{j}|j\rangle\right)=\sum_{i j} v_{i}^{*} w_{j} \delta_{i j}=\sum_{i} v_{i}^{*} w_{i} \\
    & =\left[v_{1}^{*} \ldots v_{n}^{*}\right]\left[\begin{array}{c}
    w_{1} \\
    \vdots \\
    w_{n}
    \end{array}\right].
    \end{align*}
    $$

    Thus the inner product of two vectors is equal to the vector inner product between their matrix representations, provided the representations are written with respect to the same orthonormal basis.

    Moreover, the dual vector $\langle v|$ is represented by the row vector whose components are the complex conjugates of the corresponding components of the column vector representation of $|v\rangle$.

!!! definition "Definition 2.1.20 : Outer Product"
    Define the **outer product** $|w\rangle\langle v|$ to be the linear operator from $V$ to $W$ whose action is defined by

    $$
    \begin{equation*}
    (|w\rangle\langle v|)\left(\left|v^{\prime}\right\rangle\right) \equiv|w\rangle\left\langle v \mid v^{\prime}\right\rangle=\left\langle v \mid v^{\prime}\right\rangle|w\rangle \tag{2.20}
    \end{equation*}
    $$

!!! theorem "Theorem 2.1.21 : Completeness relation"
    Let $\{|i\rangle\}$ be an orthonormal basis for the vector space $V$.
    Then

    $$
    \sum_{i}|i\rangle\langle i|=I .
    $$

    This identity is called the **completeness relation**.

    !!! proof
        Let $|v\rangle$ be an arbitrary vector in $V$.
        Since $\{|i\rangle\}$ is an orthonormal basis, we can write

        $$
        |v\rangle=\sum_{i} v_{i}|i\rangle
        $$

        for some complex numbers $v_{i}$.
        Also, $\langle i \mid v\rangle=v_{i}$.
        Therefore

        $$
        \left(\sum_{i}|i\rangle\langle i|\right)|v\rangle
        =\sum_{i}|i\rangle\langle i \mid v\rangle
        =\sum_{i} v_{i}|i\rangle
        =|v\rangle .
        $$

        Since this is true for every $|v\rangle \in V$, it follows that

        $$
        \sum_{i}|i\rangle\langle i|=I .
        $$

!!! theorem "Theorem 2.1.22 : Representing Any Operator in Outer Product Notation"
    Suppose $A: V \rightarrow W$ is a linear operator, $\left|v_{i}\right\rangle$ is an orthonormal basis for $V$, and $\left|w_{j}\right\rangle$ is an orthonormal basis for $W$.
    Using **Theorem 2.1.21** twice, we obtain

    $$
    \begin{equation*}
    A=I_{W} A I_{V} \tag{2.23}
    \end{equation*}
    $$

    $$
    \begin{align*}
    & =\sum_{i j}\left|w_{j}\right\rangle\left\langle w_{j}\right| A\left|v_{i}\right\rangle\left\langle v_{i}\right|  \tag{2.24}\\
    & =\sum_{i j}\left\langle w_{j}\right| A\left|v_{i}\right\rangle\left|w_{j}\right\rangle\left\langle v_{i}\right|, \tag{2.25}
    \end{align*}
    $$

    which is the outer product representation for $A$.

!!! theorem "Theorem 2.1.23 : Cauchy-Schwarz inequality"
    The Cauchy-Schwarz inequality is an important geometric fact about Hilbert spaces.
    For any two vectors $|v\rangle$ and $|w\rangle$,
    $$
    |\langle v \mid w\rangle|^{2} \leq\langle v \mid v\rangle\langle w \mid w\rangle.
    $$

    Equality occurs if and only if $|v\rangle$ and $|w\rangle$ are linearly related, that is, $|v\rangle=z|w\rangle$ or $|w\rangle=z|v\rangle$ for some scalar $z$.

    !!! proof
        Use **Theorem 2.1.18** to construct an orthonormal basis $|i\rangle$ for the vector space such that the first member of the basis is
        $$
        \frac{|w\rangle}{\sqrt{\langle w \mid w\rangle}}.
        $$

        Then, using **Theorem 2.1.21** and dropping some non-negative terms,
        $$
        \begin{align*}
        \langle v \mid v\rangle\langle w \mid w\rangle & =\sum_{i}\langle v \mid i\rangle\langle i \mid v\rangle\langle w \mid w\rangle \\
        & \geq \frac{\langle v \mid w\rangle\langle w \mid v\rangle}{\langle w \mid w\rangle}\langle w \mid w\rangle \\
        & =\langle v \mid w\rangle\langle w \mid v\rangle=|\langle v \mid w\rangle|^{2},
        \end{align*}
        $$

        as required.

## Eigenvectors and eigenvalues

!!! definition "Definition 2.1.24 : Eigenvector, eigenvalue, characteristic function, and eigenspace"
    An **eigenvector** of a linear operator $A$ on a vector space is a non-zero vector $|v\rangle$ such that $A|v\rangle=v|v\rangle$, where $v$ is a complex number known as the **eigenvalue** of $A$ corresponding to $|v\rangle$.

    The **characteristic function** is defined to be $c(\lambda) \equiv \operatorname{det}|A-\lambda I|$, where det is the determinant function for matrices. It depends only upon the operator $A$, and not on the specific matrix representation used for $A$.

    The solutions of the **characteristic equation** $c(\lambda)=0$ are the eigenvalues of the operator $A$. By the fundamental theorem of algebra, every polynomial has at least one complex root, so every operator $A$ has at least one eigenvalue, and a corresponding eigenvector.

    The **eigenspace** corresponding to an eigenvalue $v$ is the set of vectors which have eigenvalue $v$. It is a vector subspace of the vector space on which $A$ acts.

!!! definition "Definition 2.1.25 : Diagonal Representation"
    A **diagonal representation** for an operator $A$ on a vector space $V$ is a representation

    $$
    A=\sum_i \lambda_i |i\rangle\langle i|,
    $$

    where the vectors $|i\rangle$ form an orthonormal set of eigenvectors for $A$, with corresponding eigenvalues $\lambda_i$.

    Diagonal representations are sometimes also known as **orthonormal decompositions**.

!!! definition "Definition 2.1.26 : Degenerate Eigenspace"
    An eigenspace is said to be **degenerate** if it is more than one dimensional.

!!! example "Example 2.1.27 : Eigendecomposition of the Pauli matrices"
    The Pauli matrices $X$, $Y$, and $Z$ each have eigenvalues $+1$ and $-1$.

    For $X$, an orthonormal eigenbasis is
    $$
    |+\rangle \equiv \frac{|0\rangle+|1\rangle}{\sqrt{2}}, \qquad
    |-\rangle \equiv \frac{|0\rangle-|1\rangle}{\sqrt{2}},
    $$
    with eigenvalues $+1$ and $-1$, respectively. Therefore
    $$
    X=|+\rangle\langle+|-|-\rangle\langle-|.
    $$

    For $Y$, an orthonormal eigenbasis is
    $$
    |y_{+}\rangle \equiv \frac{|0\rangle+i|1\rangle}{\sqrt{2}}, \qquad
    |y_{-}\rangle \equiv \frac{|0\rangle-i|1\rangle}{\sqrt{2}},
    $$
    with eigenvalues $+1$ and $-1$, respectively. Therefore
    $$
    Y=|y_{+}\rangle\langle y_{+}|-|y_{-}\rangle\langle y_{-}|.
    $$

    For $Z$, the vectors $|0\rangle$ and $|1\rangle$ are eigenvectors with eigenvalues $+1$ and $-1$, respectively. Therefore
    $$
    Z=|0\rangle\langle 0|-|1\rangle\langle 1|.
    $$

    With respect to each corresponding eigenbasis, the matrix representation is diagonal:
    $$
    \left[\begin{array}{rr}
    1 & 0 \\
    0 & -1
    \end{array}\right].
    $$

## 2.1.6. Adoints and Hermitial Operators

!!! definition "Definition 2.1.28 : Adjoint (Hermitian Conjugate)"
    Suppose $A$ is any linear operator on a Hilbert space, $V$.
    Then there exists a unique linear operator $A^{\dagger}$ on $V$ such that for all vectors $|v\rangle,|w\rangle \in V$,

    $$
    (|v\rangle, A|w\rangle)=\left(A^{\dagger}|v\rangle,|w\rangle\right) \tag{2.32}
    $$

    This linear operator is known as the **adjoint** or **Hermitian conjugate** of the operator $A$.

!!! theorem "Theorem 2.1.29 : Anti-linearity of the adjoint"
    The adjoint operation is anti-linear,

    $$
    \begin{equation*}
    \left(\sum_{i} a_{i} A_{i}\right)^{\dagger}=\sum_{i} a_{i}^{*} A_{i}^{\dagger} . \tag{2.33}
    \end{equation*}
    $$

!!! theorem "Theorem 2.1.30 : Matrix representation of adjoint"
    In a matrix representation of an operator $A$, the action of the Hermitian conjugation operation is to take the matrix of $A$ to the conjugate-transpose matrix,

    $$
    A^{\dagger} \equiv\left(A^{*}\right)^{T},
    $$

    where the $*$ indicates complex conjugation, and $T$ indicates the transpose operation.
    For example, we have

    $$
    \left[\begin{array}{cc}
    1+3 i & 2 i  \tag{2.34}\\
    1+i & 1-4 i
    \end{array}\right]^{\dagger}=\left[\begin{array}{cc}
    1-3 i & 1-i \\
    -2 i & 1+4 i
    \end{array}\right]
    $$

!!! definition "Definition 2.1.31 : Hermitian or self-adjoint operator"
    An operator $A$ whose adjoint is $A$ is known as a **Hermitian** or **self-adjoint** operator.

!!! definition "Definition 2.1.32 : Projector and Orthogonal Complement"
    Let $W$ be a $k$-dimensional vector subspace of a $d$-dimensional vector space $V$.
    By **[Theorem 2.1.18](/home/arnold/arnold/github/math-notes/docs/linear-algebra/1.md)**, we may choose an orthonormal basis $|1\rangle, \ldots, |d\rangle$ for $V$ such that $|1\rangle, \ldots, |k\rangle$ is an orthonormal basis for $W$.

    The **projector** onto $W$ is

    $$
    P \equiv \sum_{i=1}^{k} |i\rangle \langle i|.
    $$

    This definition is independent of the orthonormal basis chosen for $W$.
    Since $|v\rangle\langle v|$ is Hermitian for any vector $|v\rangle$, the projector $P$ is Hermitian, so $P^{\dagger} = P$.
    We will often refer to the vector space $P$ as shorthand for the vector space onto which $P$ is a projector.

    The **orthogonal complement** of $P$ is the operator

    $$
    Q \equiv I - P.
    $$

    It is a projector onto the vector space spanned by $|k+1\rangle, \ldots, |d\rangle$.
    We also refer to that vector space as the orthogonal complement of $P$, and may denote it by $Q$.

!!! theorem "Theorem 2.1.33 : Projectors satisfy $P^{2}=P$"
    If $P$ is a projector, then

    $$
    P^{2}=P.
    $$

!!! definition "Definition 2.1.34 : normal operator"
    An operator $A$ is said to be **normal** if

    $$
    A A^{\dagger}=A^{\dagger} A.
    $$

!!! theorem "Theorem 2.1.35 : Spectral theorem"
    The spectral decomposition is an extremely useful representation theorem for normal operators.

    Any normal operator $M$ on a vector space $V$ is diagonal with respect to some orthonormal basis for $V$.
    Conversely, any diagonalizable operator is normal.

    !!! proof
        The forward implication is exactly the spectral theorem statement: if $M$ is normal, then there exists an orthonormal basis for $V$ with respect to which $M$ is diagonal.

        For the converse, suppose that $M$ is diagonalizable.
        By **Definition 2.1.25**, $M$ has a diagonal representation with respect to some orthonormal basis of eigenvectors.
        In that same orthonormal basis, $M^{\dagger}$ is also diagonal, so $M M^{\dagger}=M^{\dagger} M$.
        Hence $M$ is normal by **Definition 2.1.34**.

!!! theorem "Theorem 2.1.36 : A normal matrix is Hermitian if and only if it has real eigenvalues"
    A normal matrix is Hermitian if and only if it has real eigenvalues.

!!! definition "Definition 2.1.37 : unitary"
    An operator $U$ is **unitary** if $U^{\dagger} U=I$.

!!! theorem "Theorem 2.1.38 : Unitary operators preserve inner products"
    If $U$ is unitary and $|v\rangle$, $|w\rangle$ are any two vectors, then

    $$
    (U|v\rangle, U|w\rangle)=\langle v| U^{\dagger} U|w\rangle=\langle v| I|w\rangle=\langle v \mid w\rangle.
    $$

    Thus unitary operators preserve inner products between vectors.

    !!! proof
        Since $U^{\dagger} U=I$,

        $$
        (U|v\rangle, U|w\rangle)=\langle v| U^{\dagger} U|w\rangle=\langle v| I|w\rangle=\langle v \mid w\rangle.
        $$

!!! concept "Concept 2.1.39 : outer product representation of a unitary"
    Let $\left|v_{i}\right\rangle$ be any orthonormal basis set, and define $\left|w_{i}\right\rangle \equiv U\left|v_{i}\right\rangle$ for a unitary operator $U$. Then $\left|w_{i}\right\rangle$ is also an orthonormal basis set, since unitary operators preserve inner products, and

    $$
    U=\sum_{i}\left|w_{i}\right\rangle\left\langle v_{i}\right|.
    $$

    Conversely, if $\left|v_{i}\right\rangle$ and $\left|w_{i}\right\rangle$ are any two orthonormal bases, then the operator defined by

    $$
    U \equiv \sum_{i}\left|w_{i}\right\rangle\left\langle v_{i}\right|
    $$

    is unitary.

!!! theorem "Theorem 2.1.40"
    All eigenvalues of a unitary matrix have modulus $1$.
    Equivalently, every eigenvalue can be written in the form $e^{i\theta}$ for some real $\theta$.

!!! example "Example 2.1.41 : Pauli matrices are Hermitian and unitary"
    The Pauli matrices are Hermitian and unitary.

!!! theorem "Theorem 2.1.42"
    All eigenvalues of a unitary matrix have modulus $1$, that is, can be written in the form $e^{i \theta}$ for some real $\theta$.

!!! example "Example 2.1.43 : Pauli matrices are Hermitian and unitary"
    The Pauli matrices are Hermitian and unitary.

!!! theorem "Theorem 2.1.44 : Change of basis matrix"
    Let

    $$
    U \equiv \sum_i |w_i\rangle\langle v_i|
    $$

    be the unitary operator determined by the two orthonormal bases $\left\{|v_i\rangle\right\}$ and $\left\{|w_i\rangle\right\}$, so that $U|v_i\rangle=|w_i\rangle$ for each $i$.
    If $A^{\prime}$ and $A^{\prime \prime}$ are the matrix representations of an operator $A$ with respect to these two bases, then $A^{\prime \prime}$ is unitarily similar to $A^{\prime}$.
    More explicitly, if the matrix of $U$ in the basis $\left\{|v_i\rangle\right\}$ is denoted again by $U$, then

    $$
    A^{\prime \prime}=U^{\dagger} A^{\prime} U .
    $$

    !!! proof
        Since $|w_i\rangle=U|v_i\rangle$, we also have $\langle w_i|=\langle v_i|U^{\dagger}$.
        Therefore

        $$
        A_{i j}^{\prime \prime}=\langle w_i| A|w_j\rangle=\langle v_i| U^{\dagger} A U|v_j\rangle .
        $$

        Thus $A^{\prime \prime}$ is the matrix representation of $U^{\dagger} A U$ in the basis $\left\{|v_i\rangle\right\}$.

        If $U_{k i}=\langle v_k|w_i\rangle$, then

        $$
        |w_i\rangle=\sum_k U_{k i}|v_k\rangle .
        $$

        Hence

        $$
        \begin{aligned}
        A_{i j}^{\prime \prime}
        &= \langle w_i| A|w_j\rangle \\
        &= \sum_{k, \ell} U_{k i}^{*}\langle v_k| A|v_{\ell}\rangle U_{\ell j} \\
        &= \sum_{k, \ell} \left(U^{\dagger}\right)_{i k} A_{k \ell}^{\prime} U_{\ell j},
        \end{aligned}
        $$

        which is exactly the $(i,j)$ entry of $U^{\dagger} A^{\prime} U$.
        Therefore

        $$
        A^{\prime \prime}=U^{\dagger} A^{\prime} U .
        $$

!!! definition "Definition 2.1.45 : positive operator, positive definite operator"
    A **positive operator** $A$ is an operator such that for any vector $|v\rangle$, $(|v\rangle, A|v\rangle)$ is a real, non-negative number.

    If $(|v\rangle, A|v\rangle)$ is strictly greater than zero for all $|v\rangle \neq 0$, then we say that $A$ is **positive definite**.

!!! theorem "Theorem 2.1.46 : Hermiticity of positive operators"
    Every positive operator in **Definition 2.1.45** is Hermitian.

    !!! proof
        Let $A$ be a positive operator, and let $|x\rangle$ and $|y\rangle$ be arbitrary vectors.
        By positivity,
        \[
        (|x\rangle, A|x\rangle), \qquad (|y\rangle, A|y\rangle)
        \]
        are real.
        Also,
        \[
        (|x\rangle + |y\rangle, A(|x\rangle + |y\rangle))
        \]
        is real, so after expansion
        \[
        (|x\rangle, A|y\rangle) + (|y\rangle, A|x\rangle)
        \]
        is real.

        Similarly,
        \[
        (|x\rangle + i|y\rangle, A(|x\rangle + i|y\rangle))
        \]
        is real, and expanding gives
        \[
        i(|x\rangle, A|y\rangle) - i(|y\rangle, A|x\rangle)
        \]
        is real.

        Write
        \[
        \alpha = (|x\rangle, A|y\rangle), \qquad \beta = (|y\rangle, A|x\rangle).
        \]
        Since $\alpha + \beta$ is real,
        \[
        \overline{\alpha} + \overline{\beta} = \alpha + \beta.
        \]
        Since $i(\alpha - \beta)$ is real,
        \[
        -i(\overline{\alpha} - \overline{\beta}) = i(\alpha - \beta),
        \]
        and therefore
        \[
        \overline{\alpha} - \overline{\beta} = -\alpha + \beta.
        \]
        Adding the two relations yields $\overline{\alpha} = \beta$, that is,
        \[
        (|y\rangle, A|x\rangle) = \overline{(|x\rangle, A|y\rangle)} = (A|y\rangle, |x\rangle).
        \]
        Renaming the vectors, we obtain
        \[
        (|x\rangle, A|y\rangle) = (A|x\rangle, |y\rangle)
        \]
        for all $|x\rangle$ and $|y\rangle$.
        Hence $A$ is Hermitian.

!!! theorem "Theorem 2.1.47 : $A^{\dagger} A$ is positive"
    For any operator $A$, $A^{\dagger} A$ is positive.

## Tensor Products

!!! definition "Definition 2.1.48 : tensor product"
    Suppose $V$ and $W$ are vector spaces of dimension $m$ and $n$, respectively. For convenience, suppose also that $V$ and $W$ are Hilbert spaces. Then $V \otimes W$ (read "$V$ tensor $W$") is an $mn$-dimensional vector space whose elements are linear combinations of tensor products $|v\rangle \otimes|w\rangle$, where $|v\rangle \in V$ and $|w\rangle \in W$.

    If $|i\rangle$ and $|j\rangle$ are orthonormal bases for $V$ and $W$, then $|i\rangle \otimes|j\rangle$ is a basis for $V \otimes W$.

    We often abbreviate $|v\rangle \otimes|w\rangle$ by writing $|v\rangle|w\rangle$, $|v, w\rangle$, or even $|v w\rangle$.

!!! theorem "Theorem 2.1.49 : basic properties of tensor product"
    By definition, the tensor product satisfies the following basic properties.

    1. For an arbitrary scalar $z$ and elements $|v\rangle$ of $V$ and $|w\rangle$ of $W$,

        $$
        \begin{equation*}
        z(|v\rangle \otimes|w\rangle)=(z|v\rangle) \otimes|w\rangle=|v\rangle \otimes(z|w\rangle) \tag{2.42}
        \end{equation*}
        $$

    2. For arbitrary $\left|v_{1}\right\rangle$ and $\left|v_{2}\right\rangle$ in $V$ and $|w\rangle$ in $W$,

        $$
        \begin{equation*}
        \left(\left|v_{1}\right\rangle+\left|v_{2}\right\rangle\right) \otimes|w\rangle=\left|v_{1}\right\rangle \otimes|w\rangle+\left|v_{2}\right\rangle \otimes|w\rangle . \tag{2.43}
        \end{equation*}
        $$

    3. For arbitrary $|v\rangle$ in $V$ and $\left|w_{1}\right\rangle$ and $\left|w_{2}\right\rangle$ in $W$,

        $$
        \begin{equation*}
        |v\rangle \otimes\left(\left|w_{1}\right\rangle+\left|w_{2}\right\rangle\right)=|v\rangle \otimes\left|w_{1}\right\rangle+|v\rangle \otimes\left|w_{2}\right\rangle . \tag{2.44}
        \end{equation*}
        $$

!!! definition "Definition 2.1.50 : tensor product of two operators"
    Suppose $|v\rangle$ and $|w\rangle$ are vectors in $V$ and $W$, and $A$ and $B$ are linear operators on $V$ and $W$, respectively.
    The **tensor product of two operators** is the linear operator $A \otimes B$ on $V \otimes W$ defined by

    $$
    (A \otimes B)(|v\rangle \otimes |w\rangle) \equiv A|v\rangle \otimes B|w\rangle .
    $$

    This definition is extended to all elements of $V \otimes W$ in the natural way to ensure linearity:

    $$
    (A \otimes B)\left(\sum_i a_i |v_i\rangle \otimes |w_i\rangle\right)
    \equiv
    \sum_i a_i A|v_i\rangle \otimes B|w_i\rangle .
    $$

    It can be shown that $A \otimes B$ defined in this way is a well-defined linear operator on $V \otimes W$.

!!! definition "Definition 2.1.51 : inner products in tensor products"
    The inner products on the spaces $V$ and $W$ can be used to define a natural inner product on $V \otimes W$.
    Define

    $$
    \left(\sum_{i} a_{i}\left|v_{i}\right\rangle \otimes\left|w_{i}\right\rangle, \sum_{j} b_{j}\left|v_{j}^{\prime}\right\rangle \otimes\left|w_{j}^{\prime}\right\rangle\right) \equiv \sum_{i j} a_{i}^{*} b_{j}\left\langle v_{i} \mid v_{j}^{\prime}\right\rangle\left\langle w_{i} \mid w_{j}^{\prime}\right\rangle .
    \tag{2.49}
    $$

!!! definition "Definition 2.1.52 : Kronecker product"
    Suppose $A$ is an $m$ by $n$ matrix, and $B$ is a $p$ by $q$ matrix.
    The **Kronecker product** has the matrix representation

    $$
    A \otimes B \equiv \overbrace{\left[\begin{array}{cccc}
    A_{11} B & A_{12} B & \ldots & A_{1 n} B \\
    A_{21} B & A_{22} B & \ldots & A_{2 n} B \\
    \vdots & \vdots & \vdots & \vdots \\
    A_{m 1} B & A_{m 2} B & \ldots & A_{m n} B
    \end{array}\right]}^{n q}\} m p
    $$

!!! definition "Definition 2.1.53 : power notation of tensor products"
    The notation $|\psi\rangle^{\otimes k}$ means that $|\psi\rangle$ is tensored with itself $k$ times.
    For example,
    $$
    |\psi\rangle^{\otimes 2}=|\psi\rangle \otimes |\psi\rangle.
    $$
    An analogous notation is also used for operators on tensor product spaces.

!!! theorem "Theorem 2.1.54 : Tensor product is not commutative"
    The tensor product is not commutative. In particular, calculating the matrix representations of the tensor products of the Pauli operators $X$ and $Z$, $I$ and $X$, and $X$ and $I$ shows that changing the order of the factors can change the tensor product.

!!! theorem "Theorem 2.1.55 : complex conjugation, transpose, and adjoint distribute over the tensor product"
    $$
    (A \otimes B)^{*}=A^{*} \otimes B^{*}, \qquad
    (A \otimes B)^{T}=A^{T} \otimes B^{T}, \qquad
    (A \otimes B)^{\dagger}=A^{\dagger} \otimes B^{\dagger}.
    $$

!!! theorem "Theorem 2.1.56 : Tensor products preserve unitary, Hermitian, positive, and projector structure"
    Let $A$ and $B$ be operators.

    - If $A$ and $B$ are **unitary**, then $A \otimes B$ is unitary.
    - If $A$ and $B$ are **Hermitian**, then $A \otimes B$ is Hermitian.
    - If $A$ and $B$ are **positive**, then $A \otimes B$ is positive.
    - If $A$ and $B$ are **projectors**, then $A \otimes B$ is a projector.

!!! theorem "Theorem 2.1.57 : Tensor product expansion of the Hadamard transform"
    The Hadamard transform on $n$ qubits, $H^{\otimes n}$, may be written as

    $$
    \begin{equation*}
    H^{\otimes n}=\frac{1}{\sqrt{2^{n}}} \sum_{x, y}(-1)^{x \cdot y}|x\rangle\langle y| . \tag{2.55}
    \end{equation*}
    $$

## Operator Functions

!!! definition "Definition 2.1.58 : Operator functions"
    Let $f$ be a function from the complex numbers to the complex numbers. If
    $A=\sum_{a} a|a\rangle\langle a|$
    is a spectral decomposition for a normal operator $A$, define

    $$
    f(A) \equiv \sum_{a} f(a)|a\rangle\langle a|.
    $$

    This construction defines a corresponding matrix function on normal matrices, or on a subclass such as the Hermitian matrices. The matrix $f(A)$ is uniquely defined.

!!! theorem "Theorem 2.1.59 : Exponential of the Pauli matrices"
    Let $\vec{v}$ be any real, three-dimensional unit vector and $\theta$ a real number. Then

    $$
    \exp (i \theta \vec{v} \cdot \vec{\sigma})=\cos (\theta) I+i \sin (\theta) \vec{v} \cdot \vec{\sigma}
    $$

    where $\vec{v} \cdot \vec{\sigma} \equiv \sum_{i=1}^{3} v_{i} \sigma_{i}$.

!!! definition "Definition 2.1.60 : trace of a matrix"
    The **trace** of $A$ is defined to be the sum of its diagonal elements,

    $$
    \operatorname{tr}(A) \equiv \sum_{i} A_{i i}
    $$

!!! theorem "Theorem 2.1.61 : Properties of trace of a matrix"
    Let $A$ and $B$ be arbitrary matrices, and let $z$ be a complex number. Then the trace satisfies the following properties.

    1. It is cyclic:
       $$
       \operatorname{tr}(A B)=\operatorname{tr}(B A).
       $$

    2. It is linear:
       $$
       \operatorname{tr}(A+B)= \operatorname{tr}(A)+\operatorname{tr}(B), \qquad \operatorname{tr}(z A)=z \operatorname{tr}(A).
       $$

    3. It is invariant under the unitary similarity transformation $A \rightarrow U A U^{\dagger}$:
       $$
       \operatorname{tr}\left(U A U^{\dagger}\right)= \operatorname{tr}\left(U^{\dagger} U A\right)=\operatorname{tr}(A).
       $$

!!! definition "Definition 2.1.62 : trace of an operator"
    The **trace** of an operator $A$ is defined to be the trace of any matrix representation of $A$.
    The invariance of the trace under unitary similarity transformations ensures that the trace of an operator is well defined.

!!! theorem "Theorem 2.1.63 : $\operatorname{tr}(A|\psi\rangle\langle\psi|)=\langle\psi|A|\psi\rangle$"
    If $|\psi\rangle$ is a unit vector and $A$ is an arbitrary operator, then
    $$
    \operatorname{tr}(A|\psi\rangle\langle\psi|)=\langle\psi|A|\psi\rangle.
    $$

    !!! proof
        Use **Theorem 2.1.18** to extend $|\psi\rangle$ to an orthonormal basis $\{|i\rangle\}$ which includes $|\psi\rangle$ as the first element.
        Then
        $$
        \begin{align*}
        \operatorname{tr}(A|\psi\rangle\langle\psi|)
        &= \sum_{i}\langle i| A|\psi\rangle\langle\psi \mid i\rangle \\
        &= \langle\psi| A|\psi\rangle
        \end{align*}
        $$

!!! example "Example 2.1.64 : Trace of the Pauli matrices"
    The Pauli matrices except for $I$ have trace zero.

!!! definition "Definition 2.1.65 : Hilbert-Schmidt inner product on operators"
    Let $V$ be a Hilbert space, and let $L_{V}$ denote the set of linear operators on $V$.
    The **Hilbert-Schmidt inner product** (or **trace inner product**) on $L_{V}$ is the function on $L_{V} \times L_{V}$ defined by

    $$
    (A, B) \equiv \operatorname{tr}\left(A^{\dagger} B\right).
    $$

    This gives the vector space $L_{V}$ a natural inner product structure, turning it into a Hilbert space.

## Commutator and Anti-Commutator

!!! definition "Definition 2.1.66 : commutator, commutes"
    The **commutator** between two operators $A$ and $B$ is defined to be

    $$
    [A, B] \equiv A B-B A
    $$

    If $[A, B]=0$, that is, if $A B=B A$, then we say that $A$ **commutes** with $B$.

!!! definition "Definition 2.1.67 : anti-commutator"
    The **anti-commutator** of two operators $A$ and $B$ is defined by

    $$
    \begin{equation*}
    \{A, B\} \equiv A B+B A \tag{2.67}
    \end{equation*}
    $$

    We say that $A$ **anti-commutes** with $B$ if $\{A, B\}=0$.

!!! theorem "Theorem 2.1.68 : Simultaneous diagonalization theorem"
    Suppose $A$ and $B$ are Hermitian operators.
    Then $[A, B]=0$ if and only if there exists an orthonormal basis such that both $A$ and $B$ are diagonal with respect to that basis.
    In this case, we say that $A$ and $B$ are **simultaneously diagonalizable**.

!!! example "Example 2.1.69 : Commutation relations for the Pauli matrices"
    The Pauli matrices satisfy the commutation relations

    $$
    [X, Y]=2 i Z ; \quad [Y, Z]=2 i X ; \quad [Z, X]=2 i Y .
    $$

    There is an elegant way to write these relations using $\epsilon_{j k l}$, the antisymmetric tensor on three indices, for which $\epsilon_{j k l}=0$ except for $\epsilon_{123}=\epsilon_{231}=\epsilon_{312}=1$, and $\epsilon_{321}=\epsilon_{213}=\epsilon_{132}=-1$:

    $$
    \left[\sigma_{j}, \sigma_{k}\right]=2 i \sum_{l=1}^{3} \epsilon_{j k l} \sigma_{l} .
    $$

!!! theorem "Theorem 2.1.70 : tensor product properties and operator tensor products"
    By definition, the tensor product satisfies the following basic properties.

    (1) For an arbitrary scalar $z$ and elements $|v\rangle$ of $V$ and $|w\rangle$ of $W$,

    $$
    \begin{equation*}
    z(|v\rangle \otimes|w\rangle)=(z|v\rangle) \otimes|w\rangle=|v\rangle \otimes(z|w\rangle) \tag{2.42}
    \end{equation*}
    $$

    (2) For arbitrary $\left|v_{1}\right\rangle$ and $\left|v_{2}\right\rangle$ in $V$ and $|w\rangle$ in $W$,

    $$
    \begin{equation*}
    \left(\left|v_{1}\right\rangle+\left|v_{2}\right\rangle\right) \otimes|w\rangle=\left|v_{1}\right\rangle \otimes|w\rangle+\left|v_{2}\right\rangle \otimes|w\rangle . \tag{2.43}
    \end{equation*}
    $$

    (3) For arbitrary $|v\rangle$ in $V$ and $\left|w_{1}\right\rangle$ and $\left|w_{2}\right\rangle$ in $W$,

    $$
    \begin{equation*}
    |v\rangle \otimes\left(\left|w_{1}\right\rangle+\left|w_{2}\right\rangle\right)=|v\rangle \otimes\left|w_{1}\right\rangle+|v\rangle \otimes\left|w_{2}\right\rangle . \tag{2.44}
    \end{equation*}
    $$

    Suppose $|v\rangle$ and $|w\rangle$ are vectors in $V$ and $W$, and $A$ and $B$ are linear operators on $V$ and $W$, respectively.
    Then we define a linear operator $A \otimes B$ on $V \otimes W$ by

    $$
    \begin{equation*}
    (A \otimes B)(|v\rangle \otimes|w\rangle) \equiv A|v\rangle \otimes B|w\rangle . \tag{2.45}
    \end{equation*}
    $$

    The definition of $A \otimes B$ extends to all elements of $V \otimes W$ by linearity:

    $$
    \begin{equation*}
    (A \otimes B)\left(\sum_{i} a_{i}\left|v_{i}\right\rangle \otimes\left|w_{i}\right\rangle\right) \equiv \sum_{i} a_{i} A\left|v_{i}\right\rangle \otimes B\left|w_{i}\right\rangle . \tag{2.46}
    \end{equation*}
    $$

    It can be shown that $A \otimes B$ defined in this way is a well-defined linear operator on $V \otimes W$.
    This notion extends in the obvious way to the case where $A: V \rightarrow V^{\prime}$ and $B: W \rightarrow W^{\prime}$ map between different vector spaces.
    Indeed, an arbitrary linear operator $C$ mapping $V \otimes W$ to $V^{\prime} \otimes W^{\prime}$ can be represented as a linear combination of tensor products of operators mapping $V$ to $V^{\prime}$ and $W$ to $W^{\prime}$,

    $$
    \begin{equation*}
    C=\sum_{i} c_{i} A_{i} \otimes B_{i} \tag{2.47}
    \end{equation*}
    $$

## The Polar and Singular Value Decomposition

!!! theorem "Theorem 2.1.71 : Polar decomposition"
    Let $A$ be a linear operator on a vector space $V$. Then there exist a unitary operator $U$ and positive operators $J$ and $K$ such that

    $$
    A = UJ = KU,
    $$

    where the unique positive operators $J$ and $K$ satisfying these equations are defined by

    $$
    J \equiv \sqrt{A^{\dagger} A}
    \quad \text{and} \quad
    K \equiv \sqrt{A A^{\dagger}}.
    $$

    Moreover, if $A$ is invertible, then $U$ is unique.

!!! theorem "Theorem 2.1.72 : Singular value decomposition"
    Let $A$ be a square matrix. Then there exist unitary matrices $U$ and $V$, and a diagonal matrix $D$ with non-negative entries such that

    $$
    A=U D V \tag{2.80}
    $$

    The diagonal elements of $D$ are called the singular values of $A$.

!!! example "Example 2.1.73 : Polar decomposition of positive, unitary, and Hermitian matrices"
    For a positive matrix $P$,

    $$
    P^{\dagger} P=P^{2},
    $$

    so the positive part is

    $$
    J=\sqrt{P^{\dagger} P}=\sqrt{P^{2}}=P.
    $$

    Hence a polar decomposition of $P$ is

    $$
    P=I P=P I.
    $$

    For a unitary matrix $U$,

    $$
    U^{\dagger} U=U U^{\dagger}=I,
    $$

    so

    $$
    J=K=I.
    $$

    Thus the polar decomposition is

    $$
    U=U I=I U.
    $$

    For a Hermitian matrix $H$, we have $H^{\dagger}=H$, and therefore

    $$
    J=\sqrt{H^{\dagger} H}=\sqrt{H^{2}}.
    $$

    If

    $$
    H=\sum_{i} \lambda_{i}|i\rangle\langle i|,
    $$

    then

    $$
    \sqrt{H^{2}}=\sum_{i}\left|\lambda_{i}\right||i\rangle\langle i|.
    $$

    Taking

    $$
    S=\sum_{\lambda_{i} \geq 0}|i\rangle\langle i|-\sum_{\lambda_{i}<0}|i\rangle\langle i|,
    $$

    we obtain

    $$
    H=S \sqrt{H^{2}}=\sqrt{H^{2}} S.
    $$

    Thus the polar decomposition of a Hermitian matrix is its sign part times its absolute value.

!!! example "Example 2.1.74 : Polar decomposition of a normal matrix in outer product representation"
    Let $M$ be a normal matrix. By **Theorem 2.1.35**, there is an orthonormal basis $\{|i\rangle\}$ such that

    $$
    M=\sum_i \lambda_i |i\rangle \langle i|.
    $$

    Write each nonzero eigenvalue in polar form as $\lambda_i=|\lambda_i| e^{i \theta_i}$.
    Then the positive part of the polar decomposition is

    $$
    J=\sum_i |\lambda_i| |i\rangle \langle i|,
    $$

    and one corresponding unitary part is

    $$
    U=\sum_{\lambda_i \neq 0} e^{i \theta_i} |i\rangle \langle i|+\sum_{\lambda_i=0} e^{i \phi_i} |i\rangle \langle i|,
    $$

    where each $e^{i \phi_i}$ has modulus $1$.
    Therefore

    $$
    M=U J=J U.
    $$

    In particular, if $M$ is invertible, then

    $$
    U=\sum_i \frac{\lambda_i}{|\lambda_i|} |i\rangle \langle i|
    $$

    and

    $$
    M=\left(\sum_i \frac{\lambda_i}{|\lambda_i|} |i\rangle \langle i|\right)\left(\sum_i |\lambda_i| |i\rangle \langle i|\right).
    $$
