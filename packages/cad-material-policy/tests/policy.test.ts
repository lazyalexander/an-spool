import assert from 'node:assert/strict';
import test from 'node:test';
import {appearanceKit,completionTask} from '../index.js';
test('material adoption resolves only the current host evidence and rejects late decisions', async t => {
  const {verifyMaterial}=await import('../index.js');
  const scope={document:'handwheel',part:'grip',revision:7};
  const evidence={
    schema:'cad-material-evidence-v1' as const, part:scope.part,
    source:{document:scope.document,epoch:'test-epoch',revision:scope.revision},
    artifact:{release:'a'.repeat(64),revision:'b'.repeat(64)},
    material:{finish:'walnut',color:'#4a2c23',metallic:0,roughness:0.8},
  };
  const controller=new AbortController();
  let mode='adopt', issuedId='', reads=0, decisions=0;
  const turn:import('../index.js').MaterialTurn=async(permitted,read)=>{
    const proof=await read(mode==='outside-scope' ? {...permitted,revision:8} : permitted);
    decisions++;
    if (mode==='adopt') issuedId=proof.evidence_id;
    if (mode==='cancelled') controller.abort(new Error('Lookup cancelled'));
    return {adopt:true,evidence_id:issuedId};
  };
  const verify=(signal:AbortSignal=new AbortController().signal)=>verifyMaterial(scope,
    async()=>{reads++;return evidence;},signal,turn);

  assert.equal(await verify(),evidence);
  mode='previous-id';
  await assert.rejects(verify(),/did not adopt/);
  mode='outside-scope';
  await assert.rejects(verify(),/exceeded the approved scope/);
  assert.equal(reads,2);
  assert.equal(decisions,2);
  mode='wrong-source';
  await assert.rejects(verifyMaterial(scope,
    async()=>({...evidence,source:{...evidence.source,revision:8}}),new AbortController().signal,turn),/does not match the approved scope/);
  assert.equal(decisions,2);
  mode='cancelled';
  await assert.rejects(verify(controller.signal),/Lookup cancelled/);
});

test('a denied or repeated lookup cannot be repaired by returning a previously issued ID',async()=>{
  const {verifyMaterial}=await import('../index.js');
  const scope={document:'handwheel',part:'grip',revision:7};
  const evidence={schema:'cad-material-evidence-v1' as const,part:'grip',
    source:{document:'handwheel',epoch:'e',revision:7},artifact:{release:'a'.repeat(64),revision:'b'.repeat(64)},
    material:{finish:'walnut',color:'#4a2c23',metallic:0,roughness:0.8}};
  let reads=0;
  for (const args of [scope,{...scope,part:'other'}]) {
    await assert.rejects(verifyMaterial(scope,async()=>{reads++;return evidence;},new AbortController().signal,
      async(permitted,read)=>{
        const proof=await read(permitted);
        await read(args).catch(()=>{});
        return {adopt:true,evidence_id:proof.evidence_id};
      }),/did not adopt/);
  }
  assert.equal(reads,2);
  let deniedReads=0;
  await assert.rejects(verifyMaterial(scope,async()=>{deniedReads++;return evidence;},new AbortController().signal,
    async(permitted,read)=>{
      await read({...permitted,revision:8}).catch(()=>{});
      await read(permitted).catch(()=>{});
      return {adopt:false,evidence_id:''};
    }),/did not adopt/);
  assert.equal(deniedReads,0,'An out-of-scope attempt revokes the remaining read grant');
});


test('completion only proposes missing parts and reused evidence avoids model calls',async()=>{
  const surface={finish:'steel',color:'#808080',metallic:1,roughness:0.4};
  const brief={description:'test',direction:'',supplied:{},missing:{jaw:{label:'jaw'}}};
  assert.deepEqual(completionTask(brief)?.scope.parts,['jaw']);
  assert.equal(completionTask({...brief,missing:{}}),null);
  const evidence={schema:'cad-material-evidence-v1' as const,part:'jaw',
    source:{document:'vise',epoch:'e',revision:1},artifact:{release:'a',revision:'b'},material:surface};
  let calls=0;
  const result=await appearanceKit(brief,evidence,async()=>{calls++;return {};});
  assert.equal(calls,0);assert.equal(result.needsModel,false);assert.match(result.code!,/steel/);
  await assert.rejects(appearanceKit(brief,undefined,async()=>({other:surface})),/Unexpected/);
  await assert.rejects(appearanceKit(brief,undefined,async()=>({jaw:{...surface,roughness:2}})),/Invalid/);
});
