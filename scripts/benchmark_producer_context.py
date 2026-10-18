"""Offline context-size comparison with the real MCP schemas and a fixture project.

Run from mcp_server: uv run python ../scripts/benchmark_producer_context.py
No model calls or Live edits. Character counts are not token counts or billing estimates.
"""
import asyncio
import json
import os
import tempfile


async def benchmark():
    from ableton_claude import server, producer_intelligence as intelligence
    from ableton_claude.desktop_agent import EXCLUDED
    raw = await server.mcp.list_tools()
    catalog = [{'name': t.name, 'description': t.description or '', 'parameters': t.inputSchema}
               for t in raw if t.name not in EXCLUDED]
    brief = server.producer_brief()
    overview = {'tempo': 124, 'signature': '4/4', 'tracks': [
        {'i': i, 'name': 'Fixture Track %d' % i, 'vol_db': -8, 'devices': ['Utility'], 'clips_active': 4}
        for i in range(12)]}
    profile = server.knowledge.get('deep_house')
    output = []
    for task in ['Melhore o groove', 'Dê mais impacto ao drop', 'Deixe minha faixa mais profissional', 'Crie uma ideia do zero']:
        groups = intelligence.task_groups(task)
        selected = intelligence.select_tools(catalog, groups)
        old = len(brief) + len(json.dumps(catalog, ensure_ascii=False))
        new = len(intelligence.system_prompt('deep_house', overview, profile, brief, groups)) + len(json.dumps(selected, ensure_ascii=False))
        output.append({'task': task, 'old_characters': old, 'new_characters': new,
                       'reduction_percent': round((1 - new / old) * 100, 1),
                       'old_tools': len(catalog), 'new_tools': len(selected)})
    print(json.dumps({'fixture': '12-track project; real schemas; genre conventions, no trained fixture profile',
                      'metric': 'system + tool schema characters, not measured tokens or total request usage',
                      'results': output}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='producer-benchmark-') as root:
        os.environ['ABLETON_CLAUDE_DATA'] = root
        asyncio.run(benchmark())
