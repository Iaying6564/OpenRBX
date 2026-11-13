#include "v8kernel/Pair.h"

#include "decomp.h"
#include "util/Math.h"
#include "util/Velocity.h"
#include "v8kernel/Body.h"

#include <cstddef>

namespace RBX {

// FUNCTION: WEBSERVICE 0x1011cfc0
// FUNCTION: ROBLOX 0x006550a0
GeoPair::GeoPair()
{
	body0 = NULL;
	body1 = NULL;
	offset0 = NULL;
	offset1 = NULL;
}

// FUNCTION: WEBSERVICE 0x1011cfe0
// FUNCTION: ROBLOX 0x006550c0
void GeoPair::forceToBodies(const Vector3& _force, const Vector3& _position)
{
	body0->accumulateForce(-_force, _position);
	body1->accumulateForce(_force, _position);
}

// FUNCTION: WEBSERVICE 0x1011d040
// FUNCTION: ROBLOX 0x00655120
void GeoPair::computeNormalPerpVel(float& normalVel, Vector3& perpVel, const PairParams& _params)
{
	Vector3 v0 = body0->getPV().linearVelocityAtPoint(_params.position);
	Vector3 v1 = body1->getPV().linearVelocityAtPoint(_params.position);

	Vector3 vel = v1 - v0;

	normalVel = _params.normal.dot(vel);

	perpVel = vel - _params.normal * normalVel;
}

// FUNCTION: WEBSERVICE 0x1011d1a0
// FUNCTION: ROBLOX 0x00655280
void GeoPair::computeBallBall(PairParams& _params)
{
	const Vector3& pos0 = body0->getPos();
	const Vector3& pos1 = body1->getPos();

	_params.normal = pos1 - pos0;
	_params.length = _params.normal.unitize() - pairData.radiusSum;
	_params.position = pos0 + _params.normal * pairData.radius0;
}

// FUNCTION: WEBSERVICE 0x1011d240
// FUNCTION: ROBLOX 0x00655320
void GeoPair::computeBallPoint(PairParams& _params)
{
	const Vector3& pos0 = body0->getPos();

	_params.position = body1->getCoordinateFrame().pointToWorldSpace(*offset1);
	_params.normal = _params.position - pos0;
	_params.length = _params.normal.unitize() - pairData.radius0;
}

// FUNCTION: WEBSERVICE 0x1011d320
// FUNCTION: ROBLOX 0x00655400
void GeoPair::computeBallEdge(PairParams& _params)
{
	const Vector3& pos0 = body0->getPos();
	const CoordinateFrame& coord1 = body1->getCoordinateFrame();

	Vector3 edgePoint = coord1.pointToWorldSpace(*offset1);

	Vector3 edge = Math::getWorldNormal(pairData.normalID1, coord1);

	Vector3 delta = edgePoint - pos0;

	_params.normal = delta - edge * delta.dot(edge);

	_params.position = pos0 + _params.normal;
	_params.length = _params.normal.unitize() - pairData.radius0;
}

// FUNCTION: WEBSERVICE 0x1011d480
// FUNCTION: ROBLOX 0x00655560
void GeoPair::computeBallPlane(PairParams& _params)
{
	const Vector3& pos0 = body0->getPos();
	const CoordinateFrame& coord1 = body1->getCoordinateFrame();
	Vector3 planePoint = coord1.pointToWorldSpace(*offset1);

	_params.normal = -Math::getWorldNormal(pairData.normalID1, coord1);

	Vector3 delta = planePoint - pos0;

	Vector3 toPlane = _params.normal * delta.dot(_params.normal);

	_params.position = pos0 + toPlane;
	_params.length = toPlane.magnitude() - pairData.radius0;
}

// FUNCTION: WEBSERVICE 0x1011d5e0
// FUNCTION: ROBLOX 0x006556c0
void GeoPair::computePointPlane(PairParams& _params)
{
	_params.position = body0->getCoordinateFrame().pointToWorldSpace(*offset0);

	const CoordinateFrame& coord1 = body1->getCoordinateFrame();

	Vector3 planePoint = coord1.pointToWorldSpace(*offset1);

	_params.normal = -Math::getWorldNormal(pairData.normalID1, coord1);

	_params.length = (planePoint - _params.position).dot(_params.normal);
}

// FUNCTION: WEBSERVICE 0x1011d770
// FUNCTION: ROBLOX 0x00655850
void GeoPair::computeEdgeEdgePlane(PairParams& _params)
{
	const CoordinateFrame& coord0 = body0->getCoordinateFrame();
	const CoordinateFrame& coord1 = body1->getCoordinateFrame();

	Vector3 pa = coord0.pointToWorldSpace(*offset0);
	Vector3 pPlane = coord1.pointToWorldSpace(*offset1);

	Vector3 e0 = Math::getWorldNormal(pairData.normalID0, coord0);
	Vector3 ub = Math::getWorldNormal(pairData.normalID1, coord1);

	Vector3 p = pPlane - pa;

	float dot = ub.dot(e0);
	float d = 1.0f - dot * dot;

	_params.normal = -Math::getWorldNormal(pairData.planeID, coord1);

	if (d > 1e-05) {
		float t0 = p.dot(e0);
		float t1 = -p.dot(ub);

		float t = (t1 * dot + t0) / d;

		if (6.0f < fabs(t)) {
			t = 6.0f * Math::sign(t);
		}

		_params.position = pa + e0 * t;
		_params.length = (pPlane - _params.position).dot(_params.normal);
	}
	else {
		_params.position = pa;
		_params.length = 0.0f;
	}
}

// FUNCTION: WEBSERVICE 0x1011daf0
// FUNCTION: ROBLOX 0x00655bd0
void GeoPair::computeEdgeEdge(PairParams& _params)
{
	const CoordinateFrame& ca = body0->getCoordinateFrame();
	const CoordinateFrame& cb = body1->getCoordinateFrame();

	Vector3 pa = ca.pointToWorldSpace(*offset0);
	Vector3 pb = cb.pointToWorldSpace(*offset1);

	Vector3 ua = Math::getWorldNormal(pairData.normalID0, ca);
	Vector3 ub = Math::getWorldNormal(pairData.normalID1, cb);

	Vector3 p = pb - pa;
	float uaub = ua.dot(ub);
	float q1 = ua.dot(p);
	float q2 = -ub.dot(p);
	float d = 1 - uaub * uaub;
	if (d > 1e-6f) {
		d = 1.0f / d;
		float alpha = (q1 + uaub * q2) * d;
		float beta = (uaub * q1 + q2) * d;
		pa = pa + alpha * ua;
		pb = pb + beta * ub;
		_params.position = 0.5 * (pa + pb);
		_params.normal = pa - pb;
		_params.length = -_params.normal.unitize();
	}
	else {
		_params.position = pa;
		_params.normal = ua;
		_params.length = 0.0; // hopefully will blow out;
	}
}

} // namespace RBX
