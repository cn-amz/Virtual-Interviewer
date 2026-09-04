from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.auth import get_current_user
from app.ability_tree import hydrate_tree_from_reports
from app.ability_organizer import deterministic_organize, organize_with_text_model
from app.ability_tree_markdown import write_ability_tree_markdown
from app.config import Settings, get_settings
from app.integrations.bailian.text_client import BailianTextClient, BailianTextConfig
from app.storage import JsonStorage

router = APIRouter(prefix="/api/ability-trees", tags=["ability-trees"])


def get_storage(settings: Settings = Depends(get_settings)) -> JsonStorage:
    return JsonStorage(settings.data_dir)


def prepare_tree(storage: JsonStorage, user_id: str) -> tuple[dict, str]:
    tree = storage.read_ability_tree(user_id)
    if tree is None:
        raise HTTPException(status_code=404, detail="Ability tree not found")
    tree = hydrate_tree_from_reports(tree, storage.list_interviews())
    if not tree.get("question_groups") or not tree.get("type_branches"):
        tree = deterministic_organize(tree)
    storage.write_ability_tree(user_id, tree)
    markdown_path = write_ability_tree_markdown(storage.data_dir, user_id, tree)
    return tree, f"obsidian://open?path={quote(markdown_path.as_posix(), safe='')}"


@router.get("/{user_id}")
def get_ability_tree(
    user_id: str,
    settings: Settings = Depends(get_settings),
    storage: JsonStorage = Depends(get_storage),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    tree, obsidian_uri = prepare_tree(storage, user_id)
    return {**tree, "markdown_path": str(settings.data_dir / "ability_graphs" / user_id / "index.md"), "obsidian_uri": obsidian_uri}


@router.get("/{user_id}/markdown", response_class=PlainTextResponse)
def get_ability_tree_markdown(
    user_id: str,
    settings: Settings = Depends(get_settings),
    _current_user: dict = Depends(get_current_user),
) -> PlainTextResponse:
    storage = JsonStorage(settings.data_dir)
    tree, _ = prepare_tree(storage, user_id)
    path = settings.data_dir / "ability_graphs" / user_id / "index.md"
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@router.post("/{user_id}/organize")
async def organize_ability_tree(
    user_id: str,
    settings: Settings = Depends(get_settings),
    storage: JsonStorage = Depends(get_storage),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    tree, _ = prepare_tree(storage, user_id)
    text_client = None
    if settings.text_mode == "bailian_text":
        text_client = BailianTextClient(
            BailianTextConfig(
                api_key=settings.dashscope_api_key,
                model=settings.bailian_text_model,
                base_url=settings.bailian_text_base_url,
            ),
            system_prompt="你是能力树整理器，只输出符合要求的 JSON。",
        )
    organized = await organize_with_text_model(tree, text_client)
    storage.write_ability_tree(user_id, organized)
    write_ability_tree_markdown(storage.data_dir, user_id, organized)
    return {
        **organized,
        "markdown_path": str(settings.data_dir / "ability_graphs" / user_id / "index.md"),
        "obsidian_uri": f"obsidian://open?path={quote((settings.data_dir / 'ability_graphs' / user_id / 'index.md').as_posix(), safe='')}",
    }
