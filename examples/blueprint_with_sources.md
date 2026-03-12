# 2.1. Linear Algebra

- **def : complex vector space**

  > "The basic objects of linear algebra are vector spaces. The vector space of most interest to us is $\mathbf{C}^{n}$, the space of all $n$-tuples of complex numbers, $(z_{1}, \ldots, z_{n})$. The elements of a vector space are called vectors ... There is an addition operation defined which takes pairs of vectors to other vectors ... Furthermore, in a vector space there is a multiplication by a scalar operation ... where $z$ is a scalar, that is, a complex number, and the multiplications on the right are ordinary multiplication of complex numbers. Physicists sometimes refer to complex numbers as $c$-numbers." (§2.1, eqs. 2.1–2.3)

- **con : quantum mechanical notation for a vector (braket notation), column vector notation**

  > "Quantum mechanics is our main motivation for studying linear algebra, so we will use the standard notation of quantum mechanics for linear algebraic concepts. The standard quantum mechanical notation for a vector in a vector space is the following: $|\psi\rangle$. $\psi$ is a label for the vector (any label is valid, although we prefer to use simple labels like $\psi$ and $\varphi$). The $|\cdot\rangle$ notation is used to indicate that the object is a vector. The entire object $|\psi\rangle$ is sometimes called a ket, although we won't use that terminology often." (§2.1, eq. 2.4)
  >
  > Column vector notation: "we will sometimes use the column matrix notation $\begin{bmatrix} z_1 \\ \vdots \\ z_n \end{bmatrix}$ to indicate a vector." (§2.1, eq. 2.1)

- **def : zero vector**

  > "A vector space also contains a special zero vector, which we denote by 0. It satisfies the property that for any other vector $|v\rangle$, $|v\rangle + 0 = |v\rangle$. Note that we do not use the ket notation for the zero vector — it is the only exception we shall make. The reason for making the exception is because it is conventional to use the 'obvious' notation for the zero vector, $|0\rangle$, to mean something else entirely. The scalar multiplication operation is such that $z0 = 0$ for any complex number $z$. ... In $\mathbf{C}^{n}$ the zero element is $(0, 0, \ldots, 0)$." (§2.1)

- **def : vector subspace**

  > "A vector subspace of a vector space $V$ is a subset $W$ of $V$ such that $W$ is also a vector space, that is, $W$ must be closed under scalar multiplication and addition." (§2.1)

---

## 2.1.1. Bases and Linear Independence

- **def : spanning set, span, linear combination**

  > "A spanning set for a vector space is a set of vectors $|v_1\rangle, \ldots, |v_n\rangle$ such that any vector $|v\rangle$ in the vector space can be written as a linear combination $|v\rangle = \sum_i a_i |v_i\rangle$ of vectors in that set." (§2.1.1)
  >
  > "We say that the vectors $|v_1\rangle$ and $|v_2\rangle$ span the vector space $\mathbf{C}^2$." (§2.1.1)

- **ex : two different spanning sets for C^2**

  > First spanning set: $|v_1\rangle \equiv \begin{bmatrix}1\\0\end{bmatrix}$, $|v_2\rangle \equiv \begin{bmatrix}0\\1\end{bmatrix}$, since any $|v\rangle = \begin{bmatrix}a_1\\a_2\end{bmatrix}$ can be written as $a_1|v_1\rangle + a_2|v_2\rangle$. (eq. 2.5–2.6)
  >
  > Second spanning set: $|v_1\rangle \equiv \frac{1}{\sqrt{2}}\begin{bmatrix}1\\1\end{bmatrix}$, $|v_2\rangle \equiv \frac{1}{\sqrt{2}}\begin{bmatrix}1\\-1\end{bmatrix}$, since $|v\rangle = \frac{a_1+a_2}{\sqrt{2}}|v_1\rangle + \frac{a_1-a_2}{\sqrt{2}}|v_2\rangle$. (eqs. 2.7–2.8)

- **def : linearly dependent, linearly independent, basis, dimension, finite dimensional vector space**

  > "A set of non-zero vectors $|v_1\rangle, \ldots, |v_n\rangle$ are linearly dependent if there exists a set of complex numbers $a_1, \ldots, a_n$ with $a_i \neq 0$ for at least one value of $i$, such that $a_1|v_1\rangle + a_2|v_2\rangle + \cdots + a_n|v_n\rangle = 0$. A set of vectors is linearly independent if it is not linearly dependent. It can be shown that any two sets of linearly independent vectors which span a vector space $V$ contain the same number of elements. We call such a set a basis for $V$. Furthermore, such a basis set always exists. The number of elements in the basis is defined to be the dimension of $V$. In this book we will only be interested in finite dimensional vector spaces." (§2.1.1, eq. 2.9)

---

## 2.1.2. Linear Operators and Matrices

- **def : linear operator, identity operator, zero operator**

  > "A linear operator between vector spaces $V$ and $W$ is defined to be any function $A: V \rightarrow W$ which is linear in its inputs, $A\!\left(\sum_i a_i |v_i\rangle\right) = \sum_i a_i A(|v_i\rangle)$. Usually we just write $A|v\rangle$ to denote $A(|v\rangle)$. When we say that a linear operator $A$ is defined on a vector space $V$, we mean that $A$ is a linear operator from $V$ to $V$. An important linear operator on any vector space $V$ is the identity operator, $I_V$, defined by the equation $I_V|v\rangle \equiv |v\rangle$ for all vectors $|v\rangle$. ... Another important linear operator is the zero operator, which we denote 0. The zero operator maps all vectors to the zero vector, $0|v\rangle \equiv 0$." (§2.1.2, eq. 2.10)

- **def : composition**

  > "Suppose $V$, $W$, and $X$ are vector spaces, and $A: V \rightarrow W$ and $B: W \rightarrow X$ are linear operators. Then we use the notation $BA$ to denote the composition of $B$ with $A$, defined by $(BA)(|v\rangle) \equiv B(A(|v\rangle))$. Once again, we write $BA|v\rangle$ as an abbreviation for $(BA)(|v\rangle)$." (§2.1.2)

- **con : matrix representation**

  > "The most convenient way to understand linear operators is in terms of their matrix representations. ... Suppose $A: V \rightarrow W$ is a linear operator between vector spaces $V$ and $W$. Suppose $|v_1\rangle, \ldots, |v_m\rangle$ is a basis for $V$ and $|w_1\rangle, \ldots, |w_n\rangle$ is a basis for $W$. Then for each $j$ in the range $1, \ldots, m$, there exist complex numbers $A_{1j}$ through $A_{nj}$ such that $A|v_j\rangle = \sum_i A_{ij}|w_i\rangle$. The matrix whose entries are the values $A_{ij}$ is said to form a matrix representation of the operator $A$. This matrix representation of $A$ is completely equivalent to the operator $A$, and we will use the matrix representation and abstract operator viewpoints interchangeably. Note that to make the connection between matrices and linear operators we must specify a set of input and output basis states for the input and output vector spaces of the linear operator." (§2.1.2, eq. 2.12)

---

## 2.1.3. The Pauli Matrices

- **def : pauli matrices I, X, Y, Z**

  > "Four extremely useful matrices which we shall often have occasion to use are the Pauli matrices. These are 2 by 2 matrices, which go by a variety of notations. ... $\sigma_0 \equiv I \equiv \begin{bmatrix}1&0\\0&1\end{bmatrix}$, $\sigma_1 \equiv \sigma_x \equiv X \equiv \begin{bmatrix}0&1\\1&0\end{bmatrix}$, $\sigma_2 \equiv \sigma_y \equiv Y \equiv \begin{bmatrix}0&-i\\i&0\end{bmatrix}$, $\sigma_3 \equiv \sigma_z \equiv Z \equiv \begin{bmatrix}1&0\\0&-1\end{bmatrix}$." (§2.1.3, Figure 2.2)

---

## 2.1.4. Inner Products

- **def : inner products, quantum mechanical notation for inner product, inner product space**

  > "An inner product is a function which takes as input two vectors $|v\rangle$ and $|w\rangle$ from a vector space and produces a complex number as output. ... The standard quantum mechanical notation for the inner product $(|v\rangle, |w\rangle)$ is $\langle v|w\rangle$, where $|v\rangle$ and $|w\rangle$ are vectors in the inner product space ... A function $(\cdot,\cdot)$ from $V \times V$ to $\mathbf{C}$ is an inner product if it satisfies the requirements that: (1) $(\cdot,\cdot)$ is linear in the second argument ... (2) $(|v\rangle,|w\rangle)=(|w\rangle,|v\rangle)^*$. (3) $(|v\rangle,|v\rangle) \geq 0$ with equality if and only if $|v\rangle=0$. ... We call a vector space equipped with an inner product an inner product space." (§2.1.4, eqs. 2.13–2.14)

- **def : dual vector**

  > "... the notation $\langle v|$ is used for the dual vector to the vector $|v\rangle$; the dual is a linear operator from the inner product space $V$ to the complex numbers $\mathbf{C}$, defined by $\langle v|(|w\rangle) \equiv \langle v|w\rangle \equiv (|v\rangle, |w\rangle)$. We will see shortly that the matrix representation of dual vectors is just a row vector." (§2.1.4)

- **thm : conjugate-linear in first argument (exercise 2.6)**

  > "Exercise 2.6: Show that any inner product $(\cdot,\cdot)$ is conjugate-linear in the first argument, $\left(\sum_i \lambda_i |w_i\rangle, |v\rangle\right) = \sum_i \lambda_i^* \left(|w_i\rangle, |v\rangle\right)$." (§2.1.4, eq. 2.15)

- **ex : inner product defined in C^n**

  > "For example, $\mathbf{C}^{n}$ has an inner product defined by $\left((y_1,\ldots,y_n),(z_1,\ldots,z_n)\right) \equiv \sum_i y_i^* z_i = [y_1^* \ldots y_n^*]\begin{bmatrix}z_1\\\vdots\\z_n\end{bmatrix}$." (§2.1.4, eq. 2.14)

- **con : hilbert space**

  > "Discussions of quantum mechanics often refer to Hilbert space. In the finite dimensional complex vector spaces that come up in quantum computation and quantum information, a Hilbert space is exactly the same thing as an inner product space. From now on we use the two terms interchangeably, preferring the term Hilbert space. In infinite dimensions Hilbert spaces satisfy additional technical restrictions above and beyond inner product spaces, which we will not need to worry about." (§2.1.4)

- **def : orthogonal, orthonormal, norm, normalized, orthonormal set**

  > "Vectors $|w\rangle$ and $|v\rangle$ are orthogonal if their inner product is zero. ... We define the norm of a vector $|v\rangle$ by $\||v\rangle\| \equiv \sqrt{\langle v|v\rangle}$. A unit vector is a vector $|v\rangle$ such that $\||v\rangle\|=1$. We also say that $|v\rangle$ is normalized if $\||v\rangle\|=1$. It is convenient to talk of normalizing a vector by dividing by its norm; thus $|v\rangle/\||v\rangle\|$ is the normalized form of $|v\rangle$, for any non-zero vector $|v\rangle$. A set $|i\rangle$ of vectors with index $i$ is orthonormal if each vector is a unit vector, and distinct vectors in the set are orthogonal, that is, $\langle i|j\rangle = \delta_{ij}$." (§2.1.4, eq. 2.16)

- **thm : gram-schmidt procedure**

  > "Suppose $|w_1\rangle, \ldots, |w_d\rangle$ is a basis set for some vector space $V$ with an inner product. There is a useful method, the Gram-Schmidt procedure, which can be used to produce an orthonormal basis set $|v_1\rangle, \ldots, |v_d\rangle$ for the vector space $V$. Define $|v_1\rangle \equiv |w_1\rangle / \||w_1\rangle\|$, and for $1 \leq k \leq d-1$ define $|v_{k+1}\rangle$ inductively by $|v_{k+1}\rangle \equiv \frac{|w_{k+1}\rangle - \sum_{i=1}^k \langle v_i|w_{k+1}\rangle|v_i\rangle}{\||w_{k+1}\rangle - \sum_{i=1}^k \langle v_i|w_{k+1}\rangle|v_i\rangle\|}$. It is not difficult to verify that the vectors $|v_1\rangle, \ldots, |v_d\rangle$ form an orthonormal set which is also a basis for $V$." (§2.1.4, eq. 2.17)

- **matrix representation means matrix representation with respect to orthonormal input and output bases**

  > "From now on, when we speak of a matrix representation for a linear operator, we mean a matrix representation with respect to orthonormal input and output bases. We also use the convention that if the input and output spaces for a linear operator are the same, then the input and output bases are the same, unless noted otherwise." (§2.1.4)

- **thm : matrix representation of inner product, matrix representation of dual vector**

  > "With these conventions, the inner product on a Hilbert space can be given a convenient matrix representation. Let $|w\rangle = \sum_i w_i|i\rangle$ and $|v\rangle = \sum_j v_j|j\rangle$ be representations of vectors ... with respect to some orthonormal basis $|i\rangle$. Then, since $\langle i|j\rangle = \delta_{ij}$,
  > $\langle v|w\rangle = \sum_{ij} v_i^* w_j \delta_{ij} = \sum_i v_i^* w_i = [v_1^* \ldots v_n^*]\begin{bmatrix}w_1\\\vdots\\w_n\end{bmatrix}$.
  > That is, the inner product of two vectors is equal to the vector inner product between two matrix representations of those vectors, provided the representations are written with respect to the same orthonormal basis. We also see that the dual vector $\langle v|$ has a nice interpretation as the row vector whose components are complex conjugates of the corresponding components of the column vector representation of $|v\rangle$." (§2.1.4, eqs. 2.18–2.19)

- **def : outer product**

  > "There is a useful way of representing linear operators which makes use of the inner product, known as the outer product representation. Suppose $|v\rangle$ is a vector in an inner product space $V$, and $|w\rangle$ is a vector in an inner product space $W$. Define $|w\rangle\langle v|$ to be the linear operator from $V$ to $W$ whose action is defined by $(|w\rangle\langle v|)(|v'\rangle) \equiv |w\rangle\langle v|v'\rangle = \langle v|v'\rangle|w\rangle$." (§2.1.4, eq. 2.20)

- **thm : completeness relation**

  > "Let $|i\rangle$ be any orthonormal basis for the vector space $V$, so an arbitrary vector $|v\rangle$ can be written $|v\rangle = \sum_i v_i|i\rangle$ for some set of complex numbers $v_i$. Note that $\langle i|v\rangle = v_i$ and therefore $\left(\sum_i |i\rangle\langle i|\right)|v\rangle = \sum_i |i\rangle\langle i|v\rangle = \sum_i v_i|i\rangle = |v\rangle$. Since the last equation is true for all $|v\rangle$ it follows that $\sum_i |i\rangle\langle i| = I$. This equation is known as the completeness relation." (§2.1.4, eqs. 2.21–2.22)

- **thm : representing any operator in outer product notation**

  > "One application of the completeness relation is to give a means for representing any operator in the outer product notation. Suppose $A: V \rightarrow W$ is a linear operator, $|v_i\rangle$ is an orthonormal basis for $V$, and $|w_j\rangle$ an orthonormal basis for $W$. Using the completeness relation twice we obtain $A = I_W A I_V = \sum_{ij} |w_j\rangle\langle w_j|A|v_i\rangle\langle v_i| = \sum_{ij} \langle w_j|A|v_i\rangle|w_j\rangle\langle v_i|$, which is the outer product representation for $A$. We also see from this equation that $A$ has matrix element $\langle w_j|A|v_i\rangle$ in the $i$th column and $j$th row, with respect to the input basis $|v_i\rangle$ and output basis $|w_j\rangle$." (§2.1.4, eqs. 2.23–2.25)

- **thm : cauchy-schwartz inequality**

  > "Box 2.1: The Cauchy-Schwarz inequality is an important geometric fact about Hilbert spaces. It states that for any two vectors $|v\rangle$ and $|w\rangle$, $|\langle v|w\rangle|^2 \leq \langle v|v\rangle\langle w|w\rangle$. ... A little thought shows that equality occurs if and only if $|v\rangle$ and $|w\rangle$ are linearly related, $|v\rangle = z|w\rangle$ or $|w\rangle = z|v\rangle$, for some scalar $z$." (§2.1.4, Box 2.1, eqs. 2.26–2.28)

---

## 2.1.5. Eigenvectors and Eigenvalues

- **def : eigenvector, eigenvalue, characteristic function, eigenspace**

  > "An eigenvector of a linear operator $A$ on a vector space is a non-zero vector $|v\rangle$ such that $A|v\rangle = v|v\rangle$, where $v$ is a complex number known as the eigenvalue of $A$ corresponding to $|v\rangle$. ... The characteristic function is defined to be $c(\lambda) \equiv \det|A - \lambda I|$, where det is the determinant function for matrices ... The solutions of the characteristic equation $c(\lambda) = 0$ are the eigenvalues of the operator $A$. By the fundamental theorem of algebra, every polynomial has at least one complex root, so every operator $A$ has at least one eigenvalue, and a corresponding eigenvector. The eigenspace corresponding to an eigenvalue $v$ is the set of vectors which have eigenvalue $v$. It is a vector subspace of the vector space on which $A$ acts." (§2.1.5)

- **def : diagonal representation (on orthonormal basis), orthonormal decomposition**

  > "A diagonal representation for an operator $A$ on a vector space $V$ is a representation $A = \sum_i \lambda_i |i\rangle\langle i|$, where the vectors $|i\rangle$ form an orthonormal set of eigenvectors for $A$, with corresponding eigenvalues $\lambda_i$. An operator is said to be diagonalizable if it has a diagonal representation. ... Diagonal representations are sometimes also known as orthonormal decompositions." (§2.1.5)

- **def : degenerate eigenspace**

  > "When an eigenspace is more than one dimensional we say that it is degenerate. For example, the matrix $A \equiv \begin{bmatrix}2&0&0\\0&2&0\\0&0&0\end{bmatrix}$ has a two-dimensional eigenspace corresponding to the eigenvalue 2. The eigenvectors $(1,0,0)$ and $(0,1,0)$ are said to be degenerate because they are linearly independent eigenvectors of $A$ with the same eigenvalue." (§2.1.5, eq. 2.30)

- **ex : eigendecomposition of pauli matrices**

  > "Exercise 2.11: (Eigendecomposition of the Pauli matrices) Find the eigenvectors, eigenvalues, and diagonal representations of the Pauli matrices $X$, $Y$, and $Z$." (§2.1.5)
  >
  > Example given in the text: "note that the Pauli $Z$ matrix may be written $Z = \begin{bmatrix}1&0\\0&-1\end{bmatrix} = |0\rangle\langle 0| - |1\rangle\langle 1|$ where the matrix representation is with respect to orthonormal vectors $|0\rangle$ and $|1\rangle$, respectively." (§2.1.5, eq. 2.29)

---

## 2.1.6. Adjoints and Hermitian Operators

- **def : adjoint (hermitian conjugate)**

  > "Suppose $A$ is any linear operator on a Hilbert space, $V$. It turns out that there exists a unique linear operator $A^\dagger$ on $V$ such that for all vectors $|v\rangle, |w\rangle \in V$, $(|v\rangle, A|w\rangle) = (A^\dagger|v\rangle, |w\rangle)$. This linear operator is known as the adjoint or Hermitian conjugate of the operator $A$. From the definition it is easy to see that $(AB)^\dagger = B^\dagger A^\dagger$. By convention, if $|v\rangle$ is a vector, then we define $|v\rangle^\dagger \equiv \langle v|$. With this definition it is not difficult to see that $(A|v\rangle)^\dagger = \langle v|A^\dagger$." (§2.1.6, eq. 2.32)

- **thm : anti-linearity of adjoint**

  > "Exercise 2.14: (Anti-linearity of the adjoint) Show that the adjoint operation is anti-linear, $\left(\sum_i a_i A_i\right)^\dagger = \sum_i a_i^* A_i^\dagger$." (§2.1.6, eq. 2.33)

- **thm : matrix representation of adjoint**

  > "In a matrix representation of an operator $A$, the action of the Hermitian conjugation operation is to take the matrix of $A$ to the conjugate-transpose matrix, $A^\dagger \equiv (A^*)^T$, where the $*$ indicates complex conjugation, and $T$ indicates the transpose operation. For example, we have $\begin{bmatrix}1+3i & 2i \\ 1+i & 1-4i\end{bmatrix}^\dagger = \begin{bmatrix}1-3i & 1-i \\ -2i & 1+4i\end{bmatrix}$." (§2.1.6, eq. 2.34)

- **def : self-adjoint (hermitian)**

  > "An operator $A$ whose adjoint is $A$ is known as a Hermitian or self-adjoint operator." (§2.1.6)

- **def : projectors, orthogonal complement**

  > "An important class of Hermitian operators is the projectors. Suppose $W$ is a $k$-dimensional vector subspace of the $d$-dimensional vector space $V$. Using the Gram-Schmidt procedure it is possible to construct an orthonormal basis $|1\rangle, \ldots, |d\rangle$ for $V$ such that $|1\rangle, \ldots, |k\rangle$ is an orthonormal basis for $W$. By definition, $P \equiv \sum_{i=1}^k |i\rangle\langle i|$ is the projector onto the subspace $W$. ... From the definition it can be shown that $|v\rangle\langle v|$ is Hermitian for any vector $|v\rangle$, so $P$ is Hermitian, $P^\dagger = P$. ... The orthogonal complement of $P$ is the operator $Q \equiv I - P$. It is easy to see that $Q$ is a projector onto the vector space spanned by $|k+1\rangle, \ldots, |d\rangle$, which we also refer to as the orthogonal complement of $P$, and may denote by $Q$." (§2.1.6, eq. 2.35)

- **thm : P^2=P iff projector (exercise 2.16)**

  > "Exercise 2.16: Show that any projector $P$ satisfies the equation $P^2 = P$." (§2.1.6)

- **def : normal operator**

  > "An operator $A$ is said to be normal if $AA^\dagger = A^\dagger A$. Clearly, an operator which is Hermitian is also normal." (§2.1.6)

- **thm : spectral theorem**

  > "There is a remarkable representation theorem for normal operators known as the spectral decomposition, which states that an operator is a normal operator if and only if it is diagonalizable." (§2.1.6)
  >
  > "Box 2.2 — Theorem 2.1: (Spectral decomposition) Any normal operator $M$ on a vector space $V$ is diagonal with respect to some orthonormal basis for $V$. Conversely, any diagonalizable operator is normal." (Box 2.2)
  >
  > "In terms of the outer product representation, this means that $M$ can be written as $M = \sum_i \lambda_i |i\rangle\langle i|$, where $\lambda_i$ are the eigenvalues of $M$, $|i\rangle$ is an orthonormal basis for $V$, and each $|i\rangle$ an eigenvector of $M$ with eigenvalue $\lambda_i$. In terms of projectors, $M = \sum_i \lambda_i P_i$, where $\lambda_i$ are again the eigenvalues of $M$, and $P_i$ is the projector onto the $\lambda_i$ eigenspace of $M$. These projectors satisfy the completeness relation $\sum_i P_i = I$, and the orthonormality relation $P_i P_j = \delta_{ij} P_i$." (Box 2.2)

- **thm : exercise 2.17**

  > "Exercise 2.17: Show that a normal matrix is Hermitian if and only if it has real eigenvalues." (§2.1.6)

- **def : unitary operator**

  > "A matrix $U$ is said to be unitary if $U^\dagger U = I$. Similarly an operator $U$ is unitary if $U^\dagger U = I$. It is easily checked that an operator is unitary if and only if each of its matrix representations is unitary. A unitary operator also satisfies $UU^\dagger = I$, and therefore $U$ is normal and has a spectral decomposition." (§2.1.6)

- **thm : unitary operator preserves inner products**

  > "Geometrically, unitary operators are important because they preserve inner products between vectors. To see this, let $|v\rangle$ and $|w\rangle$ be any two vectors. Then the inner product of $U|v\rangle$ and $U|w\rangle$ is the same as the inner product of $|v\rangle$ and $|w\rangle$: $(U|v\rangle, U|w\rangle) = \langle v|U^\dagger U|w\rangle = \langle v|I|w\rangle = \langle v|w\rangle$." (§2.1.6, eq. 2.36)

- **con : outer product representation of unitary**

  > "This result suggests the following elegant outer product representation of any unitary $U$. Let $|v_i\rangle$ be any orthonormal basis set. Define $|w_i\rangle \equiv U|v_i\rangle$, so $|w_i\rangle$ is also an orthonormal basis set, since unitary operators preserve inner products. Note that $U = \sum_i |w_i\rangle\langle v_i|$. Conversely, if $|v_i\rangle$ and $|w_i\rangle$ are any two orthonormal bases, then it is easily checked that the operator $U$ defined by $U \equiv \sum_i |w_i\rangle\langle v_i|$ is a unitary operator." (§2.1.6)

- **thm : eigenvalues of unitary matrix**

  > "Exercise 2.18: Show that all eigenvalues of a unitary matrix have modulus 1, that is, can be written in the form $e^{i\theta}$ for some real $\theta$." (§2.1.6)

- **ex : pauli matrices are hermitian and unitary**

  > "Exercise 2.19: (Pauli matrices: Hermitian and unitary) Show that the Pauli matrices are Hermitian and unitary." (§2.1.6)

- **thm : change of basis matrix**

  > "Exercise 2.20: (Basis changes) Suppose $A'$ and $A''$ are matrix representations of an operator $A$ on a vector space $V$ with respect to two different orthonormal bases, $|v_i\rangle$ and $|w_i\rangle$. Then the elements of $A'$ and $A''$ are $A'_{ij} = \langle v_i|A|v_j\rangle$ and $A''_{ij} = \langle w_i|A|w_j\rangle$. Characterize the relationship between $A'$ and $A''$." (§2.1.6)

- **def : positive operator, positive definite operator**

  > "A positive operator $A$ is defined to be an operator such that for any vector $|v\rangle$, $(|v\rangle, A|v\rangle)$ is a real, non-negative number. If $(|v\rangle, A|v\rangle)$ is strictly greater than zero for all $|v\rangle \neq 0$ then we say that $A$ is positive definite." (§2.1.6)

- **thm : hermiticity of positive operators**

  > "In Exercise 2.24 on this page you will show that any positive operator is automatically Hermitian, and therefore by the spectral decomposition has diagonal representation $\sum_i \lambda_i|i\rangle\langle i|$, with non-negative eigenvalues $\lambda_i$." (§2.1.6)
  >
  > "Exercise 2.24: (Hermiticity of positive operators) Show that a positive operator is necessarily Hermitian. (Hint: Show that an arbitrary operator $A$ can be written $A = B + iC$ where $B$ and $C$ are Hermitian.)" (§2.1.6)

- **thm : $A^\dagger A$ is positive**

  > "Exercise 2.25: Show that for any operator $A$, $A^\dagger A$ is positive." (§2.1.6)

---

## 2.1.7. Tensor Products

- **def : tensor products, orthonormal basis for tensor products, notation**

  > "The tensor product is a way of putting vector spaces together to form larger vector spaces. ... Suppose $V$ and $W$ are vector spaces of dimension $m$ and $n$ respectively. ... Then $V \otimes W$ (read '$V$ tensor $W$') is an $mn$ dimensional vector space. The elements of $V \otimes W$ are linear combinations of 'tensor products' $|v\rangle \otimes |w\rangle$ of elements $|v\rangle$ of $V$ and $|w\rangle$ of $W$. In particular, if $|i\rangle$ and $|j\rangle$ are orthonormal bases for the spaces $V$ and $W$ then $|i\rangle \otimes |j\rangle$ is a basis for $V \otimes W$. We often use the abbreviated notations $|v\rangle|w\rangle$, $|v, w\rangle$ or even $|vw\rangle$ for the tensor product $|v\rangle \otimes |w\rangle$." (§2.1.7)

- **thm : basic properties of tensor product**

  > "By definition the tensor product satisfies the following basic properties:
  > (1) For an arbitrary scalar $z$ and elements $|v\rangle$ of $V$ and $|w\rangle$ of $W$: $z(|v\rangle \otimes |w\rangle) = (z|v\rangle) \otimes |w\rangle = |v\rangle \otimes (z|w\rangle)$.
  > (2) For arbitrary $|v_1\rangle$ and $|v_2\rangle$ in $V$ and $|w\rangle$ in $W$: $(|v_1\rangle + |v_2\rangle) \otimes |w\rangle = |v_1\rangle \otimes |w\rangle + |v_2\rangle \otimes |w\rangle$.
  > (3) For arbitrary $|v\rangle$ in $V$ and $|w_1\rangle$ and $|w_2\rangle$ in $W$: $|v\rangle \otimes (|w_1\rangle + |w_2\rangle) = |v\rangle \otimes |w_1\rangle + |v\rangle \otimes |w_2\rangle$." (§2.1.7, eqs. 2.42–2.44)

- **def : linear operators in tensor products**

  > "Suppose $|v\rangle$ and $|w\rangle$ are vectors in $V$ and $W$, and $A$ and $B$ are linear operators on $V$ and $W$, respectively. Then we can define a linear operator $A \otimes B$ on $V \otimes W$ by the equation $(A \otimes B)(|v\rangle \otimes |w\rangle) \equiv A|v\rangle \otimes B|w\rangle$. ... an arbitrary linear operator $C$ mapping $V \otimes W$ to $V' \otimes W'$ can be represented as a linear combination of tensor products of operators mapping $V$ to $V'$ and $W$ to $W'$: $C = \sum_i c_i A_i \otimes B_i$." (§2.1.7, eqs. 2.45–2.48)

- **def : inner products in tensor products**

  > "The inner products on the spaces $V$ and $W$ can be used to define a natural inner product on $V \otimes W$. Define $\left(\sum_i a_i |v_i\rangle \otimes |w_i\rangle,\ \sum_j b_j |v_j'\rangle \otimes |w_j'\rangle\right) \equiv \sum_{ij} a_i^* b_j \langle v_i|v_j'\rangle\langle w_i|w_j'\rangle$. It can be shown that the function so defined is a well-defined inner product. From this inner product, the inner product space $V \otimes W$ inherits the other structure we are familiar with, such as notions of an adjoint, unitarity, normality, and Hermiticity." (§2.1.7, eq. 2.49)

- **def : kronecker product**

  > "All this discussion is rather abstract. It can be made much more concrete by moving to a convenient matrix representation known as the Kronecker product. Suppose $A$ is an $m$ by $n$ matrix, and $B$ is a $p$ by $q$ matrix. Then we have the matrix representation: $A \otimes B \equiv \begin{bmatrix}A_{11}B & A_{12}B & \cdots & A_{1n}B \\ A_{21}B & A_{22}B & \cdots & A_{2n}B \\ \vdots & \vdots & \vdots & \vdots \\ A_{m1}B & A_{m2}B & \cdots & A_{mn}B\end{bmatrix}$." (§2.1.7, eq. 2.50)

- **def : power notation of tensor products**

  > "Finally, we mention the useful notation $|\psi\rangle^{\otimes k}$, which means $|\psi\rangle$ tensored with itself $k$ times. For example $|\psi\rangle^{\otimes 2} = |\psi\rangle \otimes |\psi\rangle$. An analogous notation is also used for operators on tensor product spaces." (§2.1.7)

- **thm : tensor product is not commutative (exercise 2.27)**

  > "Exercise 2.27: Calculate the matrix representation of the tensor products of the Pauli operators (a) $X$ and $Z$; (b) $I$ and $X$; (c) $X$ and $I$. Is the tensor product commutative?" (§2.1.7)

- **thm : complex conjugate, transpose, adjoint distributes over tensor product (exercise 2.28)**

  > "Exercise 2.28: Show that the transpose, complex conjugation, and adjoint operations distribute over the tensor product, $(A \otimes B)^* = A^* \otimes B^*;\ (A \otimes B)^T = A^T \otimes B^T;\ (A \otimes B)^\dagger = A^\dagger \otimes B^\dagger$." (§2.1.7, eq. 2.53)

- **thm : tensor product of two unitary / hermitian / positive / projector is unitary / hermitian / positive / projector (exercise 2.29 ~ 2.32)**

  > "Exercise 2.29: Show that the tensor product of two unitary operators is unitary.
  > Exercise 2.30: Show that the tensor product of two Hermitian operators is Hermitian.
  > Exercise 2.31: Show that the tensor product of two positive operators is positive.
  > Exercise 2.32: Show that the tensor product of two projectors is a projector." (§2.1.7)

- **thm : tensor power of hadamard operator**

  > "Exercise 2.33: The Hadamard operator on one qubit may be written as $H = \frac{1}{\sqrt{2}}[(|0\rangle+|1\rangle)\langle 0| + (|0\rangle-|1\rangle)\langle 1|]$. Show explicitly that the Hadamard transform on $n$ qubits, $H^{\otimes n}$, may be written as $H^{\otimes n} = \frac{1}{\sqrt{2^n}} \sum_{x,y} (-1)^{x \cdot y} |x\rangle\langle y|$. Write out an explicit matrix representation for $H^{\otimes 2}$." (§2.1.7, eqs. 2.54–2.55)

---

## 2.1.8. Operator Functions

- **def : matrix function on normal matrices**

  > "Generally speaking, given a function $f$ from the complex numbers to the complex numbers, it is possible to define a corresponding matrix function on normal matrices (or some subclass, such as the Hermitian matrices) by the following construction. Let $A = \sum_a a|a\rangle\langle a|$ be a spectral decomposition for a normal operator $A$. Define $f(A) \equiv \sum_a f(a)|a\rangle\langle a|$. A little thought shows that $f(A)$ is uniquely defined. This procedure can be used, for example, to define the square root of a positive operator, the logarithm of a positive-definite operator, or the exponential of a normal operator." (§2.1.8)

- **thm : exponential of pauli matrices (exercise 2.35)**

  > "Exercise 2.35: (Exponential of the Pauli matrices) Let $\vec{v}$ be any real, three-dimensional unit vector and $\theta$ a real number. Prove that $\exp(i\theta\,\vec{v}\cdot\vec{\sigma}) = \cos(\theta)I + i\sin(\theta)\,\vec{v}\cdot\vec{\sigma}$, where $\vec{v}\cdot\vec{\sigma} \equiv \sum_{i=1}^3 v_i \sigma_i$." (§2.1.8, eq. 2.58)

- **def : trace of a matrix**

  > "Another important matrix function is the trace of a matrix. The trace of $A$ is defined to be the sum of its diagonal elements, $\operatorname{tr}(A) \equiv \sum_i A_{ii}$." (§2.1.8, eq. 2.59)

- **thm : properties of trace of a matrix (cyclic, linear, invariance under unitary similarity transformation)**

  > "The trace is easily seen to be cyclic, $\operatorname{tr}(AB) = \operatorname{tr}(BA)$, and linear, $\operatorname{tr}(A+B) = \operatorname{tr}(A)+\operatorname{tr}(B)$, $\operatorname{tr}(zA) = z\operatorname{tr}(A)$, where $A$ and $B$ are arbitrary matrices, and $z$ is a complex number. Furthermore, from the cyclic property it follows that the trace of a matrix is invariant under the unitary similarity transformation $A \rightarrow UAU^\dagger$, as $\operatorname{tr}(UAU^\dagger) = \operatorname{tr}(U^\dagger U A) = \operatorname{tr}(A)$." (§2.1.8)

- **def : trace of an operator**

  > "In light of this result, it makes sense to define the trace of an operator $A$ to be the trace of any matrix representation of $A$. The invariance of the trace under unitary similarity transformations ensures that the trace of an operator is well defined." (§2.1.8)

- **thm : tr(A |phi><phi|) = <phi|A|phi>**

  > "As an example of the trace, suppose $|\psi\rangle$ is a unit vector and $A$ is an arbitrary operator. To evaluate $\operatorname{tr}(A|\psi\rangle\langle\psi|)$ use the Gram-Schmidt procedure to extend $|\psi\rangle$ to an orthonormal basis $|i\rangle$ which includes $|\psi\rangle$ as the first element. Then we have $\operatorname{tr}(A|\psi\rangle\langle\psi|) = \sum_i \langle i|A|\psi\rangle\langle\psi|i\rangle = \langle\psi|A|\psi\rangle$. This result, that $\operatorname{tr}(A|\psi\rangle\langle\psi|) = \langle\psi|A|\psi\rangle$ is extremely useful in evaluating the trace of an operator." (§2.1.8, eqs. 2.60–2.61)

- **ex : trace of pauli matrices**

  > "Exercise 2.36: Show that the Pauli matrices except for $I$ have trace zero." (§2.1.8)

- **def : hilbert-schmidt inner product on operators**

  > "Exercise 2.39: (The Hilbert-Schmidt inner product on operators) ... An important additional result is that the vector space $L_V$ can be given a natural inner product structure, turning it into a Hilbert space. (1) Show that the function $(\cdot,\cdot)$ on $L_V \times L_V$ defined by $(A, B) \equiv \operatorname{tr}(A^\dagger B)$ is an inner product function. This inner product is known as the Hilbert-Schmidt or trace inner product." (§2.1.8, eq. 2.65)

---

## 2.1.9. Commutator and Anti-Commutator

- **def : commutator, commutes**

  > "The commutator between two operators $A$ and $B$ is defined to be $[A, B] \equiv AB - BA$. If $[A, B] = 0$, that is, $AB = BA$, then we say $A$ commutes with $B$." (§2.1.9, eq. 2.66)

- **def : anti-commutator, anti-commutes**

  > "Similarly, the anti-commutator of two operators $A$ and $B$ is defined by $\{A, B\} \equiv AB + BA$. We say $A$ anti-commutes with $B$ if $\{A, B\} = 0$." (§2.1.9, eq. 2.67)

- **thm : simultaneous diagonalization theorem**

  > "Theorem 2.2: (Simultaneous diagonalization theorem) Suppose $A$ and $B$ are Hermitian operators. Then $[A, B] = 0$ if and only if there exists an orthonormal basis such that both $A$ and $B$ are diagonal with respect to that basis. We say that $A$ and $B$ are simultaneously diagonalizable in this case." (§2.1.9)

- **ex : commutation relations for pauli matrices**

  > "Exercise 2.40: (Commutation relations for the Pauli matrices) Verify the commutation relations $[X,Y]=2iZ$; $[Y,Z]=2iX$; $[Z,X]=2iY$." (§2.1.9, eq. 2.73)
  >
  > Illustrated in the text: "$[X,Y] = \begin{bmatrix}0&1\\1&0\end{bmatrix}\begin{bmatrix}0&-i\\i&0\end{bmatrix} - \begin{bmatrix}0&-i\\i&0\end{bmatrix}\begin{bmatrix}0&1\\1&0\end{bmatrix} = 2i\begin{bmatrix}1&0\\0&-1\end{bmatrix} = 2iZ$." (eqs. 2.68–2.70)

- **thm : example 2.42 ~ 2.47**

  > "Exercise 2.42: Verify that $AB = \frac{[A,B]+\{A,B\}}{2}$." (eq. 2.77)
  >
  > "Exercise 2.43: Show that for $j,k = 1,2,3$, $\sigma_j\sigma_k = \delta_{jk}I + i\sum_{l=1}^3 \epsilon_{jkl}\sigma_l$." (eq. 2.78)
  >
  > "Exercise 2.44: Suppose $[A,B]=0$, $\{A,B\}=0$, and $A$ is invertible. Show that $B$ must be 0."
  >
  > "Exercise 2.45: Show that $[A,B]^\dagger = [B^\dagger, A^\dagger]$."
  >
  > "Exercise 2.46: Show that $[A,B] = -[B,A]$."
  >
  > "Exercise 2.47: Suppose $A$ and $B$ are Hermitian. Show that $i[A,B]$ is Hermitian." (§2.1.9)

---

## 2.1.10 The Polar and Singular Value Decomposition

- **thm : polar decomposition**

  > "Theorem 2.3: (Polar decomposition) Let $A$ be a linear operator on a vector space $V$. Then there exists unitary $U$ and positive operators $J$ and $K$ such that $A = UJ = KU$, where the unique positive operators $J$ and $K$ satisfying these equations are defined by $J \equiv \sqrt{A^\dagger A}$ and $K \equiv \sqrt{AA^\dagger}$. Moreover, if $A$ is invertible then $U$ is unique. We call the expression $A = UJ$ the left polar decomposition of $A$, and $A = KU$ the right polar decomposition of $A$." (§2.1.10, eq. 2.79)

- **thm : singular decomposition**

  > "Corollary 2.4: (Singular value decomposition) Let $A$ be a square matrix. Then there exist unitary matrices $U$ and $V$, and a diagonal matrix $D$ with non-negative entries such that $A = UDV$. The diagonal elements of $D$ are called the singular values of $A$." (§2.1.10, eq. 2.80)

- **ex : polar decomposition of positive/unitary/hermitian matrix (exercise 2.48)**

  > "Exercise 2.48: What is the polar decomposition of a positive matrix $P$? Of a unitary matrix $U$? Of a Hermitian matrix, $H$?" (§2.1.10)

- **ex : polar decomposition of normal matrix in outer product representation (exercise 2.49)**

  > "Exercise 2.49: Express the polar decomposition of a normal matrix in the outer product representation." (§2.1.10)
