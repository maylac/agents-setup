from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = ROOT / "docs/grok-bot/dispatcher-instructions.md"
SKILL = ROOT / "skills/phone-dispatcher/SKILL.md"


class DispatcherSkillParityTest(unittest.TestCase):
    def test_skill_body_matches_dispatcher_instructions(self):
        skill = SKILL.read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\n"))
        _, frontmatter, body = skill.split("---\n", 2)
        self.assertIn("name: phone-dispatcher", frontmatter)
        self.assertIn("description:", frontmatter)
        self.assertEqual(body, INSTRUCTIONS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
