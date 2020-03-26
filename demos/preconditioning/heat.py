from firedrake import *  # noqa: F403

from ufl.algorithms.ad import expand_derivatives

from IRKsome import GaussLegendre, LobattoIIIA, getForm, Dt

BT = LobattoIIIA(2)
print(BT.A)
ns = len(BT.b)
N = 64

# Single point of entry in case you want to change the size of the box.
x0 = 0.0
x1 = 10.0
y0 = 0.0
y1 = 10.0

msh = RectangleMesh(N, N, x1, y1)
V = FunctionSpace(msh, "CG", 1)
x, y = SpatialCoordinate(msh)

# Stores initial condition!
S = Constant(2.0)
C = Constant(1000.0)
tc = 0
dtc = 1. / N
dt = Constant(dtc)
t = Constant(0.0)

# We can just let these and the true solutions be expressions!
B = (x-Constant(x0))*(x-Constant(x1))*(y-Constant(y0))*(y-Constant(y1))/C
R = (x * x + y * y) ** 0.5

# This will give the exact solution at any time t.  We just have
# to t.assign(time_we_want)
uexact = B * atan(t)*(pi / 2.0 - atan(S * (R - t)))

# MMS works on symbolic differentiation of true solution, not weak form
# Except we might need to futz with this since replacement is breaking on this!
rhs = expand_derivatives(diff(uexact, t)) - div(grad(uexact))

u = interpolate(uexact, V)

# Build it once and update it rather than deepcopying in the
# time stepping loop.
unew = Function(V)

# define the variational form once outside the loop
v = TestFunction(V)
F =  inner(Dt(u), v)*dx + inner(grad(u), grad(v))*dx - inner(rhs, v)*dx

bc = DirichletBC(V, 0, "on_boundary")

# hand off the nonlinear function F to get weak form for RK method
Fnew, k, bcnew, bcdata = getForm(F, BT, t, dt, u, bcs=bc)

params = {"mat_type": "aij",
          "snes_type": "ksponly",
          "ksp_type": "gmres",
          "ksp_monitor": None,
          "pc_type": "fieldsplit",   # block preconditioner
          "pc_fieldsplit_type": "additive" # block diagaonal
}
# on each block, apply a sweep of gamg (algebraic multigrid) with default
# parameters.

per_field = {"ksp_type": "preonly",  
              "pc_type": "lu"}

num_stages = len(BT.b)

for s in range(num_stages):
    params["fieldsplit_%s" % (s,)] = per_field

ks = k.split()

prob = NonlinearVariationalProblem(Fnew, k, bcs=bcnew)
solver = NonlinearVariationalSolver(prob, solver_parameters=params)

solver.solve()
